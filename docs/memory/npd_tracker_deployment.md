---
name: npd-tracker-deployment
description: "NPD Tracker v1 + v2 deployment details for Achieve Cafe Provisions — hosting, ports, Tailscale, Google Sheets/Postgres, admin logins, supplier/product data"
metadata: 
  type: project
---

Two NPD Tracker apps run side by side on the same Windows machine, "orders-nov-23":

## v1 — `C:\Users\order\NPD-Tracker` — port 8000
Google-Sheets-backed (no Postgres). Served via `waitress` on `0.0.0.0:8000`.
- Access: `http://localhost:8000`, LAN `http://<lan-ip>:8000`, Tailscale `http://<tailscale-ip>:8000`
- Product data lives in Google Sheet (ID in v1's own DEPLOYMENT_NOTES.md), service account (email in DEPLOYMENT_NOTES.md) (key at `backend/secrets/service-account.json`, gitignored)
- Admin login: `achievecafeprovisions@gmail.com` (password in DEPLOYMENT_NOTES.md)
- 44 suppliers loaded from `NPD fields.xlsx` (Downloads folder)

## v2 — `C:\Users\order\Desktop\NPD-Tracker-v2` — port 8001
From-scratch rewrite: Postgres as source of truth, one-way Postgres → Sheets mirror, real image uploads. Served via `waitress` on `0.0.0.0:8001`.
- Access: `http://localhost:8001`, LAN `http://<lan-ip>:8001`, Tailscale `http://<tailscale-ip>:8001`
- Postgres 18 (Windows service `postgresql-x64-18`), database/role `npd_tracker_v2`; DB password and Django secret key are in `backend/.env` (gitignored) on this machine
- Mirror sheet: (ID in DEPLOYMENT_NOTES.md), tab `NPD` — reuses v1's service-account key (copied into v2's `backend/secrets/service-account.json`)
- Two admin logins: `achievecafeprovisions@gmail.com` and `bigyan@achievewholesale.com.au` (passwords in DEPLOYMENT_NOTES.md)
- **Login API differs from v1**: v2's `/api/auth/login/` expects an `email` field, not `username`
- 44 suppliers (same list as v1) + 6 products recovered from the mirror sheet's leftover data (from an earlier session's v1→v2 migration) and re-imported via `create_product` for a clean audit trail
- **Known data issue, not yet fixed**: 3 products (Apricot Goji & Almond, Macadamia Choc Fudge Brownie, Oh MG Pistachio & Coconut) have status "Will be listed - being prepared" as a placeholder guess from the original migration — needs manual correction by the user
- README/NOTES describe v2 as dev-only and never visually tested in a browser as of 2026-09-22 — worth confirming with the user whether that's since changed before treating it as equivalent to v1 in staff-facing readiness

## Shared infra
- **Tailscale**: installed, connected under `achievecafeprovisions@gmail.com` (one shared login for the whole team — anyone needing home access installs Tailscale on their own device and signs into that same account)
- **Auto-start**: both apps launch via a Startup-folder shortcut (`shell:startup`) to their own `run_server.bat`, minimized — survives reboots, verified by actually restarting through that exact path
- **Firewall**: inbound rules for TCP 8000 and 8001 both confirmed open (verified via `Test-NetConnection` + HTTP 200 over LAN and Tailscale IPs on 2026-09-24) — rules had to be added manually via an elevated PowerShell since the working session itself has no admin rights
- **Google Sign-In** is deliberately disabled on both apps (blank `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_ALLOWED_EMAIL`) since it doesn't work over raw IP addresses, which is how everyone reaches these apps — username/password only

**Why:** v1 was already staff's daily tool on the office LAN; the ask was first to add home access (Tailscale), then to stand up v2 (the Postgres/image-upload rewrite) the same way, running in parallel on a different port rather than replacing v1 outright, since v2's UI readiness for staff use hadn't been confirmed.

**How to apply:** to add a staff login on either app, use `/admin/` (Users → Add user) on the host. If the LAN or Tailscale IP ever changes, update the relevant `backend/.env` (`DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`) and restart. Full parity notes/deployment credentials are also written directly into each project folder as `DEPLOYMENT_NOTES.md` (gitignored) for anyone working from that folder directly. See [[user_role_acp]] for how this user prefers infra work explained.
