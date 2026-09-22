# NPD Tracker v2

New Product Development tracker for Achieve Cafe Provisions. Django + DRF
backend, Postgres database, React + Vite + Tailwind frontend (plain
JavaScript). A from-scratch rewrite of the original NPD Tracker (`../npd-tracker`),
built to support real photo uploads — something the original's Google-Sheets-backed
design couldn't do.

**Status: local development only.** This has not been deployed anywhere yet —
see "Running it locally" below. The original app is still what staff actually
use day to day.

## Architecture

- **`backend/`** — Django project. Product data lives in **Postgres**, not
  Google Sheets. A background sync pushes every change to a Google Sheet as a
  read-only mirror people can glance at, but the Sheet is not the source of
  truth — Postgres is.
- **`frontend/`** — React + Vite + Tailwind SPA, plain JavaScript (no
  TypeScript). In production it would be built and served by Django directly,
  same as the original app.

## One-time setup

### 1. Postgres

Install Postgres locally (or point at an existing instance) and create a
database and a role for the app:

```sql
CREATE ROLE npd_tracker_v2 WITH LOGIN PASSWORD 'choose-a-password';
CREATE DATABASE npd_tracker_v2 OWNER npd_tracker_v2;
```

### 2. Google Sheets mirror (optional)

The app works fine with this unconfigured — the Sheets sync just silently
does nothing until it's set up. To enable it:

1. In [Google Cloud Console](https://console.cloud.google.com/), reuse the
   existing service account from the original app (or create a new one and
   enable the Sheets API for it).
2. Save its key file as `backend/secrets/service-account.json` (gitignored —
   never commit it).
3. Create a new Google Sheet and **share it** with the service account's
   email as **Editor**.
4. Copy the Sheet ID from its URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`

### 3. Backend

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`: set `DB_PASSWORD` (from step 1), a real `DJANGO_SECRET_KEY`, and
`NPD_SHEET_ID` if you set up the Sheets mirror.

```
python manage.py migrate
python manage.py createsuperuser
```

### 4. Frontend

```
cd frontend
npm install
npm run build
```

This produces `frontend/dist/`, which Django serves automatically in
production.

## Running it locally

Two terminals, hot reload on both sides:

```
cd backend  &&  .venv\Scripts\activate  &&  python manage.py runserver 127.0.0.1:8010
cd frontend &&  npm run dev
```

Open `http://localhost:5173`.

(Port 8010 rather than Django's default 8000 was just to avoid colliding with
the original app's dev server if both are running at once — change it back to
whatever's free on your machine, just keep `vite.config.js`'s proxy target in
sync.)

## Field schema

`backend/products/fields_schema.py` is the single source of truth for every
product field — key, label, type, section, and display flags. The frontend's
entire form and table are generated from this at runtime (`GET /api/schema/`)
— **adding, renaming, or reflagging a field is a backend-only edit**, no
frontend code changes needed. This was true of the original app too and is
carried over deliberately.

- **`required`** — enforced both client-side and server-side
  (`services.py: _validate_required`). Currently: Date, ACP Product Name,
  Status, Active, Supplier.
- **`dashboard`** — controls what shows in the main app (table column +
  edit form). Fields without it are hidden from the main app but remain
  editable via Django Admin (`/admin/`).
- **`pipeline`** — Go-to-Market checklist fields fold into one compact
  "Checklist" column of small colored chips instead of their own columns.
- **`tableLabel`** / **`chipLabel`** — short display names for the table
  header / checklist chip, separate from the full `label` used in the form.

Unlike the original app, there's **no positional-column constraint** here —
Postgres uses named columns, so adding/removing/reordering a field is just a
normal model change + migration. The Sheets *mirror* still writes columns by
a fixed order (`products/sheets_client.py`), but that's a one-way, disposable
export — it doesn't constrain the real schema the way the original app's live
Sheet did.

## Features

Everything the original app has, rebuilt on the new stack, plus real image
uploads:

- **CRUD** with the same confirm-before-delete pattern.
- **Image galleries** — a gallery of product photos and a separate gallery of
  nutrition-label photos per product, added from the edit screen (a product
  has to be saved once before photos can be attached to it). No thumbnails or
  cropping — just capped at 10MB per file and validated as a real image.
- **CSV Import** — same two-phase preview-then-commit flow, same
  label-or-key column matching, same lenient-warnings-but-blocking-errors
  rules. Export CSV's column order doubles as the import template.
- **Supplier field** — a custom autocomplete dropdown, same UX as the
  original (locks once it matches an existing name, `+` to add a new one
  inline, delete-with-confirm per entry, blocked if still in use by a
  product) — but now backed by a real foreign key instead of a soft/free-text
  list.
- **Sortable columns**, **"stuck in status" alerts** (30+ days in a status
  that isn't an end state), **restore a deleted product**, and **in-app
  audit history** — all present, same behavior as the original.
- **Server-side validation** for required fields and numeric fields, same as
  before.

## What's different under the hood (for whoever picks this up next)

- **Yes/No fields are real booleans** in the database now, not `"Y"`/`"N"`
  text — only converted to those strings at the CSV-export and Sheets-mirror
  boundaries, where people still expect to see `Y`/`N`.
- **Supplier is a real foreign key** with referential integrity, not a
  free-text field paired with a separate curated list.
- **"Stuck in status" is a single indexed column read** (`status_changed_at`
  on the product itself), not an aggregate query over the audit log.
- **The Google Sheet is a mirror, not the database.** Every write to
  Postgres triggers a best-effort push to the Sheet afterward — if that push
  fails (network issue, permissions problem, whatever), the real save in
  Postgres is completely unaffected. The app never depends on Sheets being
  reachable.

## Notes

- All Sheets access uses a single service account — nobody signs into
  Google individually for this to work.
- Every create/update/delete writes a full field-level entry into the local
  audit log (visible at `/admin/` or via the in-app History view).
- Staff logins are separate from the Sheets connection and exist purely so
  changes can be attributed to a person.
