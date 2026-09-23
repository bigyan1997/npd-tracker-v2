# NPD Tracker v2 — Project Notes

Running notes on why this project exists, what's been decided, and what state it's in. Not a setup guide (see `README.md`; staff instructions are in `USAGE_GUIDE.md`) — this is context for whoever picks this project up next.

## Why v2 exists

v1 (`../npd-tracker`) stores actual product data in Google Sheets, not a real database — SQLite there only holds Django auth users, the curated supplier list, and the audit log. That was fine until image upload became a requirement: a gallery of product photos *and* a separate gallery of nutrition-label photos per product. Sheets cells can't hold images.

Rather than bolt image storage onto the Sheets-backed architecture, v2 is a from-scratch rewrite on **Postgres as the real source of truth**, with a **one-way Postgres → Google Sheets mirror sync** (push-only, best-effort) so the team can still glance at a familiar spreadsheet. People sometimes edit the old sheet directly — the mirror doesn't handle that; a manual edit to the mirror sheet may get silently overwritten on the next sync. Accepted tradeoff, not a bug.

v1 and v2 briefly ran side by side (ports 8000 / 8001). On **2026-09-24 v1 was retired and removed** at the user's request — v2 is the only version now. All of v1's products already existed in v2; a zip backup of v1 is kept on the host PC (see `DEPLOYMENT_NOTES.md`).

## Stack

Django + DRF backend, **Postgres** (not SQLite/Sheets), Tailwind CSS, Vite + React in **plain JavaScript** — TypeScript was deliberately dropped for v2, unlike v1.

## Status (2026-09-24)

**In use by staff**, deployed on the office PC (Waitress, port 8001), reachable on the office LAN and from home via Tailscale, and kept always on (see *Infra*). Everyone signs in with **one shared tracker login** — see *Shared-login design* below for what that forced.

Backend verified end-to-end against real Postgres; 19 automated tests (`products/tests.py`) cover Drive photos, supplier rename, edit conflicts and the Sheets header/search logic. Most UI changes have been checked by the user in the browser as they went live, but there's no automated browser testing.

## Architecture decisions that differ from v1 (all deliberate)

- **`yn`-type fields are real Postgres `BooleanField`s**, not Y/N strings. v1 used strings because Sheets cells are all strings — that constraint doesn't apply to Postgres. Booleans are translated to `"Y"`/`"N"` only at the CSV-export and Sheets-sync boundaries.
- **`supplier` is a real foreign key** to a `Supplier` table (`on_delete=PROTECT`), not v1's free-text field with a soft curated list. The "type a new name inline and it gets created" UX is preserved via `get_or_create` in the service layer — this is a data-integrity upgrade, not a UX regression. Supplier delete-while-in-use protection is now a simple `Product.objects.filter(supplier=...).count()` query instead of v1's manual full-table scan.
- **`status_changed_at`** is a real column on `Product`, updated only when the service layer detects the status field actually changed. Replaces v1's audit-log `Max(changed_at)` aggregate query for the "stuck in status" calculation (30-day threshold, excluding "Will NOT Be listed" and "Activated / Live") with a single indexed column read.
- **The schema-driven UI architecture is kept from v1.** `backend/products/fields_schema.py` is still the single source of truth for field labels/sections/types/required/dashboard/pipeline flags, served via `GET /api/schema/`. The frontend's form and table are fully generic over it. **This means schema changes are pure backend edits — the frontend needs zero code changes to pick them up.** Confirmed working live multiple times already (pipeline chip renames, removing a field from the dashboard both took effect with no frontend touch).
- **Images**: one `ProductImage` model with a `category` field (`"product"` / `"nutrition"`), not two separate models — one gallery component/API serves both. 10MB size cap, built-in decode validation, no drag-and-drop reorder. Photos picked on a brand-new product are staged in the browser and uploaded right after it's created.
- **Photos are stored in Google Drive, and Drive is the source of truth** (added 2026-09-24). They live in the `achievecafeprovisions@gmail.com` account's Drive as `NPD Tracker Photos/<Product name>/Product photos|Nutrition labels`, so staff can add/rename/move/delete photos directly in the Drive app and the tracker follows. `products/drive_sync.py` pulls each product's folder listing into `ProductImage` rows — when a product is opened in the app, and for every product every `NPD_DRIVE_SYNC_SECONDS` (default 120) from a background thread started in `wsgi.py`. Product create/rename/delete create/rename/trash its folder. Deletes are always *trash*, recoverable from Drive's Bin for 30 days.
  - That account is personal Google (not Workspace), so a service account can't own files there — the app acts as the account via an OAuth refresh token (`backend/secrets/drive-token.json`, gitignored) written by `python manage.py drive_authorize`, using a "Desktop app" OAuth client (`backend/secrets/drive-oauth-client.json`) in the same Cloud project as the Sheets service account. The OAuth app must be **published (In production)**, not "Testing", or Google expires the token after 7 days. Scope is full `drive` so the app can see photos it didn't upload itself.
  - Photos are served through the app (`/api/products/<id>/images/<image_id>/file/`, `?size=thumb` for a 400px JPEG cached in `media/photo_thumbs/`), so app-only users need no Drive access. Formats browsers can't show (iPhone HEIC etc.) are shown via Drive's own rendered preview.
  - Without the token file, uploads fall back to local disk under `media/` (dev/tests).
- **Image filenames follow a fixed convention**: `{productname}_PI_{yyyymmdd}_{shortsuffix}.ext` for product photos, `{productname}_NI_{yyyymmdd}_{shortsuffix}.ext` for nutrition-label photos, for photos uploaded through the app (files added directly in Drive keep whatever name they were given). Product name is slugified (non-alphanumeric → underscore); the short random suffix stops a second same-day upload for the same product from overwriting the first. See `products/models.py`, `product_image_filename`.
- **Restore-as-new-record** and the **audit log's denormalized-survives-deletion design** (`record_id`/`product_name_snapshot` stored as plain values, not just an FK, so history/restore work even after the product itself is deleted) were carried over unchanged from v1.
- **Sheets sync direction flips**: v1 read/wrote its sheet live on every request (the sheet *was* the database). v2's Sheets calls are a best-effort push *after* the Postgres write commits, wrapped so a Sheets API failure can never block or roll back the real write. Proven live: a product save returned success while the Sheets push failed in the background with a permissions error, and the retry succeeded once sharing was fixed.

## Added 2026-09-24

- **Shared-login design.** All staff use one tracker login, on several devices at once, so:
  - the product list refetches every 20 s (`refetchInterval`), with `keepPreviousData` so search results don't flash empty while typing; open edit forms are never overwritten;
  - **optimistic concurrency**: saves send `expectedUpdatedAt` (the `lastEditedAt` the form was opened with); `services.update_product` raises `ConflictError` → HTTP 409 if the product changed since, and the form offers "Load latest version" / "Save mine anyway" (the latter omits the timestamp). Supplier renames bump `updated_at` on affected products so a stale form can't save the old supplier name back (which would silently recreate it via `get_or_create`);
  - `GET /api/version/` returns the built JS asset name; `UpdateBanner` polls it every 5 min and offers a reload (never auto-reloads — could lose a half-filled form);
  - History can't tell people apart. Per-person tracker logins were suggested; the user chose not to for now.
- **Supplier rename** (`PATCH /api/suppliers/ {name, newName}`, pencil icon in the supplier dropdown): renames the `Supplier` row, adds a History entry per affected product, re-pushes them to the Sheet. Renaming onto another existing supplier is refused (no silent merging); case-only renames are allowed. The **+** button now always opens the Add Supplier dialog, even when a supplier is already selected.
- **Photo indicators**: Photos column in the table (`P n · N n`, missing categories in orange, "No photos" badge), a missing-photos filter, counts in the gallery headings and an empty-gallery hint linking to the product's Drive folder. No minimum photo count is enforced — only a category with zero photos is flagged.
- **Header links** to the Google Sheet and the Drive photos root folder (`GET /api/links/`, built from settings — no IDs in the frontend).
- **Search results count** ("N products found" / "0 products found" with Clear) and a filtered empty state distinct from the empty-tracker one.
- **Google Sheet fixes**: the header row was only ever written once, so after fields were renamed/removed every column from AF onward sat under the wrong heading. `ensure_tab_and_header` now rewrites the header whenever it differs and clears leftover columns. `LastEditedAt` is written in Sydney time.
- **Tests must never touch the real Sheet**: the test settings read the real `.env`, and an early test run deleted a real sheet row (restored with `sheets_push_all`). All test classes are now wrapped in `NO_SHEETS`.

## Known gaps / open items

- Restoring a deleted product creates a new record with a new, empty photo folder — its old photos stay in the trashed folder in Drive's Bin (30 days) and have to be moved back by hand.
- **CSV export** ignores the on-screen filters/sort and always comes out newest-date-first; the user was asked whether it should match the screen or go by Record ID — not decided yet.
- **Checklist redesign proposed, not built**: replace the cryptic NR/NC/ZB/BI/BS/IW/B2B chips with a progress bar + "Next: …" column and a tick-box checklist card in the form. Waiting on the user to confirm the step order and whether the two B2B image steps are sequential or either/or. Also planned with it: warn when "Nutritionals Received" is ticked but no nutrition-label photo exists.
- Filters set with the ▼ buttons on the Sheet are shared by everyone (one shared Google account).
- After an unattended Windows restart the app is down until someone logs in (fix documented in `DEPLOYMENT_NOTES.md`; needs the Microsoft-account password).

**Tests:** `products/tests.py` covers the Drive photo flow against an in-memory fake Drive. The `npd_tracker_v2` Postgres role can't create databases, so run them on SQLite via a throwaway settings module outside the repo, e.g. a `test_sqlite_settings.py` containing `from npd_tracker.settings import *` plus `DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}`, then `DJANGO_SETTINGS_MODULE=test_sqlite_settings python manage.py test products` with that file's folder on `PYTHONPATH`.

## Schema customizations already made (beyond the v1 port)

- "Loaded into Qblue Products & Supplier Price List" → renamed to **"Created in ZeaBlue Products and Supplier Price List"**.
- "Create Product into Qblue" field **deleted entirely** (column dropped from Postgres, not just hidden).
- Pipeline checklist short codes: **ZB** (ZeaBlue), **BI** (B2B image, new symbol), **BS** (B2B image, symbol swap), **IW** (Print image), **B2B** (unchanged), plus **NR**/**NC** for Nutritionals Received / Nutritionals Created into ACP Format, which were moved from separate table columns into the checklist chip group.
- "Images" (the old `imagesLocation` text field) removed from the dashboard — still editable via Django Admin, but no longer shown in the main table or add/edit form now that real photo uploads exist. Its old typed values stay in Postgres; the Sheet shows the product's Drive folder link in that column instead.
- **Every other field is now in the add/edit form** (2026-09-24). Seventeen fields — tasting/supplier descriptions, shelf life, features, units per box, supplier dates/codes/names, sample received, dimensions, weight, sell prices, ACP/Qblue/B2B names, image note — had only been editable in Django admin; they were switched on via the `dashboard` flag. `FIELDS` order was deliberately left unchanged, because the Google Sheet's columns follow it.

## Infra

- **Postgres**: local install (Windows service `postgresql-x64-18`, already running before this project started). Database `npd_tracker_v2`, owned by a dedicated role of the same name (not the `postgres` superuser). Connection details live in `backend/.env` (gitignored) — check that file directly rather than storing the password elsewhere.
- **Google Sheets mirror**: a brand-new, separate sheet from v1's (chosen deliberately, to avoid the two apps' writes colliding) — tab `NPD` (sheet ID in `DEPLOYMENT_NOTES.md` on the host PC), configured via `NPD_SHEET_ID` in `.env`. Reuses v1's existing Google service account (email in `DEPLOYMENT_NOTES.md`) rather than a new one — the credential file was copied from v1's `backend/secrets/service-account.json`. That account had to be **separately shared as Editor on the new sheet** (sharing doesn't carry over between sheets) — this caused an initial 403 error, resolved once shared.
- **Sheet photos column**: in the mirror sheet, "Photograph & Save Images — Original Images Location" is a clickable `Open photos folder` link to the product's Google Drive folder (pushed again as soon as a new product's folder is created). The old typed paths remain in Postgres, untouched. To re-send every product to the sheet (e.g. after changing what it shows, or if rows went missing): `python manage.py sheets_push_all`. Tests must never reach the real sheet — every test class is wrapped in `NO_SHEETS` (`override_settings(NPD_SHEET_ID="")`).
- **Searching the Sheet**: the data tab (`NPD`) has a frozen, bold header with filter buttons, and a separate first tab **Search** has a yellow box — type anything and matching products (name, supplier, codes, status, features) are listed below via a `FILTER` formula. Built by `SheetsClient.setup_search()` / `python manage.py sheets_setup_search`, and rebuilt automatically whenever the header row is rewritten (i.e. when fields change), so its column references stay right. The app never writes to the Search tab.
- **Always on** (host PC, 2026-09-24): the Startup-folder shortcut `NPD Tracker v2 Server.lnk` runs `run_server.bat` at login. That script restarts waitress within ~5s if it ever exits, and exits straight away if port 8001 is already being served (so it's safe to start twice). The scheduled task **"NPD Tracker v2 Keep Alive"** runs `keep_alive.vbs` → `keep_alive.ps1` every 5 minutes: if the app doesn't answer twice in a row it stops any stuck server and starts `run_server.bat` again; restarts are logged to `backend/logs/keep_alive.log`. The PC is set to never sleep on mains power, and Postgres is an automatic Windows service. Gap: both only start once someone logs in to Windows, so after an unattended reboot (e.g. Windows Update) the app is down until a login — unless the task is switched to "run whether user is logged on or not" (needs admin + the Windows password; see `DEPLOYMENT_NOTES.md`).
- **Local dev servers**: Django on `127.0.0.1:8010`, Vite on port `5173` (proxying `/api` and `/media` to the Django server).
- **Admin login**: Django superuser `admin` exists locally; password set at creation but not recorded here — reset via `manage.py changepassword admin` if needed.

## Data migrated from v1 (2026-09-22)

- **44 suppliers** imported from a reference list the user provided directly (not read from v1's live Sheets, which only had 38 curated names plus a couple of test entries like "Human and co"/"saddie" that were deliberately left out).
- **5 products** imported from v1's live Google Sheet (it only ever had 5 rows). Several data-quality issues in the source data were normalized or flagged rather than silently guessed:
  - 3 products had status `"5a. Images ready"`, not a valid status option — placeholder-mapped to **"Will be listed - being prepared"** at the user's request ("random for now"); **these need manual correction** to whatever the real status should be.
  - Several checklist fields (Image for B2B, Image for Print) had a date string like `"4-Aug-26"` instead of Yes/No — imported as **Yes**, on the reasoning that a filled-in date meant the task was actually done.
  - "Sample Received" had the literal text `"Y"` instead of a real date on 4 products — couldn't be recovered, left **blank**.
  - A few costs had a literal `"$"` prefix (e.g. `"$47.16"`) — stripped automatically, no data loss.

**Action item for the user**: review the 3 products with the placeholder "Will be listed - being prepared" status and correct them to the real status.
