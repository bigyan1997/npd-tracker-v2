# NPD Tracker v2 — Project Notes

Running notes on why this project exists, what's been decided, and what state it's in. Not a setup guide (that belongs in a future README) — this is context for whoever picks this project up next.

## Why v2 exists

v1 (`../npd-tracker`) stores actual product data in Google Sheets, not a real database — SQLite there only holds Django auth users, the curated supplier list, and the audit log. That was fine until image upload became a requirement: a gallery of product photos *and* a separate gallery of nutrition-label photos per product. Sheets cells can't hold images.

Rather than bolt image storage onto the Sheets-backed architecture, v2 is a from-scratch rewrite on **Postgres as the real source of truth**, with a **one-way Postgres → Google Sheets mirror sync** (push-only, best-effort) so the team can still glance at a familiar spreadsheet. People sometimes edit the old sheet directly — the mirror doesn't handle that; a manual edit to the mirror sheet may get silently overwritten on the next sync. Accepted tradeoff, not a bug.

Both v1 and v2 exist side by side right now. **v1 is still the one actually deployed for staff.** v2 is not deployed anywhere yet — local dev only.

## Stack

Django + DRF backend, **Postgres** (not SQLite/Sheets), Tailwind CSS, Vite + React in **plain JavaScript** — TypeScript was deliberately dropped for v2, unlike v1.

## Status (2026-09-22)

Backend: fully built and verified end-to-end against real Postgres — CRUD, dual auth (Google Sign-In + username/password), image upload, audit trail/history/restore, CSV import, and the live Sheets mirror sync were all tested via real HTTP requests, not just code review.

Frontend: fully ported to plain JS, builds cleanly (`npm run build`), dev server + API proxy verified working. **Not yet visually tested in a browser** — no browser automation tool was available, so the actual UI needs a human to click through it.

No production deployment exists for v2 — no Tailscale, no Windows service, no CI/CD. That's separate future work.

## Architecture decisions that differ from v1 (all deliberate)

- **`yn`-type fields are real Postgres `BooleanField`s**, not Y/N strings. v1 used strings because Sheets cells are all strings — that constraint doesn't apply to Postgres. Booleans are translated to `"Y"`/`"N"` only at the CSV-export and Sheets-sync boundaries.
- **`supplier` is a real foreign key** to a `Supplier` table (`on_delete=PROTECT`), not v1's free-text field with a soft curated list. The "type a new name inline and it gets created" UX is preserved via `get_or_create` in the service layer — this is a data-integrity upgrade, not a UX regression. Supplier delete-while-in-use protection is now a simple `Product.objects.filter(supplier=...).count()` query instead of v1's manual full-table scan.
- **`status_changed_at`** is a real column on `Product`, updated only when the service layer detects the status field actually changed. Replaces v1's audit-log `Max(changed_at)` aggregate query for the "stuck in status" calculation (30-day threshold, excluding "Will NOT Be listed" and "Activated / Live") with a single indexed column read.
- **The schema-driven UI architecture is kept from v1.** `backend/products/fields_schema.py` is still the single source of truth for field labels/sections/types/required/dashboard/pipeline flags, served via `GET /api/schema/`. The frontend's form and table are fully generic over it. **This means schema changes are pure backend edits — the frontend needs zero code changes to pick them up.** Confirmed working live multiple times already (pipeline chip renames, removing a field from the dashboard both took effect with no frontend touch).
- **Images**: one `ProductImage` model with a `category` field (`"product"` / `"nutrition"`), not two separate models — one gallery component/API serves both. Deliberately minimal: no thumbnail generation, no image processing beyond built-in decode validation + a 10MB size cap, no drag-and-drop reorder. Images can only be added in **edit mode** — a brand-new "New Product" form has no image section, since a product needs to exist first to have a valid upload target.
- **Image filenames follow a fixed convention**: `{productname}_PI_{yyyymmdd}_{shortsuffix}.ext` for product photos, `{productname}_NI_{yyyymmdd}_{shortsuffix}.ext` for nutrition-label photos. Product name is slugified (non-alphanumeric → underscore); the short random suffix stops a second same-day upload for the same product from overwriting the first. See `products/models.py`, `product_image_upload_path`.
- **Restore-as-new-record** and the **audit log's denormalized-survives-deletion design** (`record_id`/`product_name_snapshot` stored as plain values, not just an FK, so history/restore work even after the product itself is deleted) were carried over unchanged from v1.
- **Sheets sync direction flips**: v1 read/wrote its sheet live on every request (the sheet *was* the database). v2's Sheets calls are a best-effort push *after* the Postgres write commits, wrapped so a Sheets API failure can never block or roll back the real write. Proven live: a product save returned success while the Sheets push failed in the background with a permissions error, and the retry succeeded once sharing was fixed.

**Known gap, not fixed:** deleting a `ProductImage` (including via cascade when its parent product is deleted) removes the DB row but not the underlying file on disk. Orphaned files accumulate in `media/`. Low priority at this app's scale.

## Schema customizations already made (beyond the v1 port)

- "Loaded into Qblue Products & Supplier Price List" → renamed to **"Created in ZeaBlue Products and Supplier Price List"**.
- "Create Product into Qblue" field **deleted entirely** (column dropped from Postgres, not just hidden).
- Pipeline checklist short codes: **ZB** (ZeaBlue), **BI** (B2B image, new symbol), **BS** (B2B image, symbol swap), **IW** (Print image), **B2B** (unchanged), plus **NR**/**NC** for Nutritionals Received / Nutritionals Created into ACP Format, which were moved from separate table columns into the checklist chip group.
- "Images" (the old `imagesLocation` text field) removed from the dashboard — still editable via Django Admin, but no longer shown in the main table or add/edit form now that real photo uploads exist.

## Infra

- **Postgres**: local install (Windows service `postgresql-x64-18`, already running before this project started). Database `npd_tracker_v2`, owned by a dedicated role of the same name (not the `postgres` superuser). Connection details live in `backend/.env` (gitignored) — check that file directly rather than storing the password elsewhere.
- **Google Sheets mirror**: a brand-new, separate sheet from v1's (chosen deliberately, to avoid the two apps' writes colliding) — ID `1v9oJD37mJpVn5aAQaRHn_5RjzFnz188rbmvhWlC0MvI`, tab `NPD`, configured via `NPD_SHEET_ID` in `.env`. Reuses v1's existing Google service account (`npd-tracker-sheets@npd-tracker-508701.iam.gserviceaccount.com`) rather than a new one — the credential file was copied from v1's `backend/secrets/service-account.json`. That account had to be **separately shared as Editor on the new sheet** (sharing doesn't carry over between sheets) — this caused an initial 403 error, resolved once shared.
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
