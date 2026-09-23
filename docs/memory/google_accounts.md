---
name: google-accounts
description: Achieve's Google accounts — orders@ is personal (non-Workspace) Google; NPD v2 photos are stored in achievecafeprovisions@gmail.com's Drive (user's choice), via OAuth token
metadata:
  type: project
---

`orders@achievewholesale.com.au` is a **personal Google account (not Google Workspace)** — no "Shared drives", paid 100 GB Google One plan. Staff share Google logins rather than each having their own.

**NPD Tracker v2 photo storage owner = `achievecafeprovisions@gmail.com`** (decided 2026-09-24). The Drive sign-in happened as that account instead of orders@; when asked, the user chose to keep it. Root folder: (link in DEPLOYMENT_NOTES.md) ("NPD Tracker Photos"), layout `<Product>/Product photos|Nutrition labels`. Drive is the source of truth — staff can edit photos directly in Drive and the app syncs.

The Cloud project (project ID in DEPLOYMENT_NOTES.md) OAuth app is **published (In production)** so the refresh token doesn't expire after 7 days; a "Desktop app" client `NPD Tracker Drive` was created for this (separate from the older `NPD Tracker Web` client).

**Why:** staff wanted to upload/edit/view photos from anywhere, not only via the app, and not depend on the office PC's disk. Google Photos was rejected (no folders; API can't see photos added outside the app since 2025).

**How to apply:** personal accounts can't be written to by a service account (no quota), hence OAuth user credentials. To switch owner account: re-run `manage.py drive_authorize` signing in as the new account, then restart. Related: [[npd-tracker-deployment]], [[user-role-acp]].
