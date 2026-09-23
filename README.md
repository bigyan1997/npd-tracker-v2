# NPD Tracker v2

New Product Development tracker for Achieve Cafe Provisions. Django + DRF
backend, Postgres database, React + Vite + Tailwind frontend (plain
JavaScript), with product photos stored in Google Drive and a searchable
Google Sheet copy of every product.

A from-scratch rewrite of the original, Google-Sheets-backed NPD Tracker
(v1, retired in September 2026), built to support real photo storage.

**Status: in use.** It runs on an office Windows PC (Waitress on port 8001),
reachable on the office LAN and from home over Tailscale, kept running by a
self-restarting launcher and a keep-alive scheduled task. Host-specific
details (addresses, credentials, IDs) are in `DEPLOYMENT_NOTES.md` on that
machine — deliberately not in this public repo. Staff-facing instructions are
in [`USAGE_GUIDE.md`](USAGE_GUIDE.md); design decisions and history are in
[`NOTES.md`](NOTES.md).

## Architecture

- **`backend/`** — Django project. Product data lives in **Postgres**, which
  is the source of truth.
- **Google Sheet mirror** — every product change is pushed (best-effort, on a
  background thread) to a Google Sheet as a read-only copy. The sheet has a
  **Search** tab and filter buttons. A failed push never affects the real
  save.
- **Google Drive photos** — photos live in a Google Drive folder tree
  (`NPD Tracker Photos/<Product>/Product photos|Nutrition labels`), and
  **Drive is the source of truth for photos**: staff can add/move/delete
  photos directly in Drive and the app syncs them in (on opening a product,
  and every 2 minutes in the background). The app serves photos itself
  (cached thumbnails), so app-only users need no Drive access.
- **`frontend/`** — React + Vite + Tailwind SPA, plain JavaScript. Built into
  `frontend/dist/` and served by Django/Whitenoise.

## One-time setup

### 1. Postgres

```sql
CREATE ROLE npd_tracker_v2 WITH LOGIN PASSWORD 'choose-a-password';
CREATE DATABASE npd_tracker_v2 OWNER npd_tracker_v2;
```

### 2. Backend

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`: set `DB_PASSWORD`, a real `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`
in production, and the hosts/origins the app is reached on
(`DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`). Then:

```
python manage.py migrate
python manage.py createsuperuser
```

### 3. Google Sheets mirror (optional)

The app works without it — the sync silently does nothing until configured.

1. In Google Cloud Console, create (or reuse) a service account with the
   Sheets API enabled; save its key as `backend/secrets/service-account.json`
   (gitignored).
2. Create a Google Sheet, **share it with the service account's email as
   Editor**, and put its ID (from the URL) in `NPD_SHEET_ID`.
3. `python manage.py sheets_push_all` then `python manage.py sheets_setup_search`.

### 4. Google Drive photo storage (optional)

Without it, uploads are stored on local disk under `backend/media/`.

The photo-owning Google account is a personal (non-Workspace) account, which
a service account can't write to — so the app signs in *as* that account
with OAuth:

1. In the same Cloud project: enable the **Google Drive API**; on **Google
   Auth Platform**, fill in Branding and set the app to **In production**
   (in "Testing", Google expires the sign-in after 7 days).
2. Create an OAuth client of type **Desktop app**, download its JSON to
   `backend/secrets/drive-oauth-client.json` (gitignored).
3. `python manage.py drive_authorize` — opens a browser; sign in as the
   account that should own the photos and allow access. This writes
   `backend/secrets/drive-token.json` (gitignored); the app switches to Drive
   storage as soon as that file exists (restart the server).

### 5. Frontend

```
cd frontend
npm install
npm run build
```

## Running it

**Production (the office PC):** `run_server.bat` starts Waitress on
`0.0.0.0:8001` and restarts it if it ever stops; a Startup-folder shortcut
runs it at login, and the scheduled task "NPD Tracker v2 Keep Alive"
(`keep_alive.vbs` → `keep_alive.ps1`) restarts it if it stops answering.
A second scheduled task, "NPD Tracker v2 Auto Deploy" (`auto_deploy.vbs` →
`auto_deploy.ps1`), deploys new commits from GitHub.

**Deploying a change — just push to `main` on GitHub.** The office PC runs
`auto_deploy.ps1` every 5 minutes (scheduled task "NPD Tracker v2 Auto
Deploy"). When `main` has new commits it fast-forwards to them, installs new
packages, **runs the tests and builds the frontend while the live app keeps
running**, and only if that all passes applies migrations, swaps in the new
frontend and restarts the server (~a minute end to end). Any failure rolls
back to the previous commit and leaves the live app untouched; if the app
doesn't come back after the restart, it rolls back and restarts again.
Everything is logged to `backend/logs/auto_deploy.log` on the office PC.
Open pages then show a "new version available — Reload" banner.

It won't deploy over work done directly on the office PC: if that folder has
uncommitted changes, or commits that aren't on GitHub, it skips and says so
in the log until they're committed/pushed. Migrations are applied after the
tests pass but can't be rolled back automatically — keep them backwards
compatible.

**Working from another computer:**

```
git clone https://github.com/bigyan1997/npd-tracker-v2.git
cd npd-tracker-v2/backend
python -m venv .venv  &&  .venv\Scripts\activate  &&  pip install -r requirements.txt
cd ../frontend  &&  npm install
```

Make the change, run the tests (see *Tests* — no Postgres needed) and
`npm run build` to catch frontend errors, then commit and push to `main`.
It's live within ~5 minutes. Secrets (`.env`, `backend/secrets/`) stay on
the office PC and aren't needed for this; to run the whole app locally
you'd also need Postgres and your own `.env`.

**Deploying by hand on the office PC** (e.g. if auto-deploy is paused): for
a frontend change run `npm run build`, then `python manage.py collectstatic
--noinput`, then restart the server — all three together, because the build
immediately points `index.html` at new asset files the running server doesn't
serve until it restarts. Commit and push afterwards so auto-deploy doesn't
skip.

**Development:** two terminals, hot reload on both sides:

```
cd backend  &&  .venv\Scripts\activate  &&  python manage.py runserver 127.0.0.1:8010
cd frontend &&  npm run dev
```

Open `http://localhost:5173` (Vite proxies `/api` and `/media` to port 8010).

## Management commands

| Command | What it does |
|---|---|
| `drive_authorize` | One-time Google sign-in for Drive photo storage |
| `sheets_push_all` | Re-send every product to the Google Sheet |
| `sheets_setup_search` | (Re)build the sheet's filter buttons and Search tab |

## Tests

```
python manage.py test products
```

The app's Postgres role can't create databases, so run tests on SQLite via a
small settings module kept outside the repo:

```python
# test_sqlite_settings.py
from npd_tracker.settings import *  # noqa
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
```

`DJANGO_SETTINGS_MODULE=test_sqlite_settings python manage.py test products`
(with that file's folder on `PYTHONPATH`). Tests use an in-memory fake Google
Drive and never touch the real Google Sheet (`NO_SHEETS`).

## Field schema

`backend/products/fields_schema.py` is the single source of truth for every
product field — key, label, type, section, and display flags. The frontend's
form and table are generated from it at runtime (`GET /api/schema/`), so
**relabelling or reflagging a field is a backend-only edit**. Adding or
removing a field also needs a model change + migration.

- **`required`** — enforced client- and server-side. Currently: Date, ACP
  Product Name, Status, Active, Supplier.
- **`dashboard`** — shown in the add/edit form (every field except the
  legacy "Original Images Location"). Hidden fields stay editable in Django
  admin. Table columns are a fixed list in `ProductTable.jsx`.
- **`pipeline`** — Go-to-Market checklist fields, shown as one compact
  "Checklist" column of chips.
- **`tableLabel`** / **`chipLabel`** — short names for the table header /
  checklist chip.

The Google Sheet's columns follow the order of `FIELDS`; the sheet's header
row is rewritten automatically whenever it no longer matches.

## Features

- **Products**: add/edit/delete with confirmation, restore recently deleted
  products, full field-level **History** per product, sortable columns,
  "stuck in status" alerts (30+ days in a non-final status), CSV import
  (preview first) and export.
- **Search & filters**: search across name, supplier and codes with a live
  "N products found" count; status, active and missing-photo filters.
- **Suppliers**: autocomplete with add, **rename** (updates every product,
  logged in History) and delete (blocked while in use).
- **Planned Launch**: free-text field, shown in the form and as a table column.
- **Photos**: product and nutrition-label galleries stored in Google Drive
  (nutrition labels may also be **PDFs** — validated by content, served
  inline, previewed via Drive's first-page render),
  per-product "Open in Google Drive" links, photo counts per product in the
  table, delete warnings, cached thumbnails, HEIC support via Drive previews.
- **Shared-login safety** (all staff use one account): the product list
  auto-refreshes every 20 s; a save is refused (HTTP 409, "Load latest
  version" / "Save mine anyway") if someone else saved that product since it
  was opened; a banner offers a reload after a new deploy.
- **Google Sheet copy**: auto-updated, with an "Open photos folder" link per
  product, a Search tab and filter buttons.
