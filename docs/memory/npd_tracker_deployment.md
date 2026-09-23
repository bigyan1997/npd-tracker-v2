---
name: npd-tracker-deployment
description: "NPD Tracker v2 deployment details for Achieve Cafe Provisions (v1 removed 2026-09-24) — hosting, port 8001, Tailscale, Postgres, Sheets mirror, admin logins"
metadata:
  type: project
---

NPD Tracker v2 runs on the Windows machine "orders-nov-23". It is the only version now.

## v1 — REMOVED on 2026-09-24
At the user's request v1 (`C:\Users\order\NPD-Tracker`, Google-Sheets-backed, port 8000) was removed completely: server stopped, Startup shortcut deleted, folder deleted. All 5 products in its sheet already existed in v2. Zip backup (code, `.env`, `db.sqlite3` with v1 logins/audit log, notes, git history — no venv): `C:\Users\order\Documents\NPD-Tracker-v1-backup-2026-09-24.zip`. v1's original Google Sheet was deliberately kept. GitHub repo `bigyan1997/NPD-Tracker`: user asked for it to be deleted (done by them on github.com — `gh` CLI isn't installed here). The Windows firewall rule for TCP 8000 may still exist (removing it needs admin) — harmless.

## v2 — `C:\Users\order\Desktop\NPD-Tracker-v2` — port 8001
Postgres as source of truth, one-way Postgres → Sheets mirror, photos in Google Drive (see [[google-accounts]]). Served via `waitress` on `0.0.0.0:8001`. GitHub: `bigyan1997/npd-tracker-v2` (**public** repo — never commit secrets; no AI-tool attribution in commits or files).
- Access: `http://localhost:8001`, LAN `http://<lan-ip>:8001`, Tailscale `http://<tailscale-ip>:8001`
- Postgres 18 (Windows service `postgresql-x64-18`), database/role `npd_tracker_v2` (role can't create databases, so tests run on SQLite); DB password and Django secret key are in `backend/.env` (gitignored)
- Mirror sheet: (ID in DEPLOYMENT_NOTES.md), tab `NPD` — service account (email in DEPLOYMENT_NOTES.md), key in `backend/secrets/service-account.json`
- Two admin logins: `achievecafeprovisions@gmail.com` (password in DEPLOYMENT_NOTES.md) and `bigyan@achievewholesale.com.au` (password in DEPLOYMENT_NOTES.md)
- Login API `/api/auth/login/` expects an `email` field, not `username`
- Staff all share one tracker login (2026-09-24). So: product list auto-refreshes every 20s, saves send `expectedUpdatedAt` (409 on conflict → "Load latest"/"Save mine anyway"), and a banner offers reload after deploys. History therefore can't show who changed what — I suggested per-person logins; user chose not to for now.
- 44 suppliers + 6 products
- **Known data issue, not yet fixed**: 3 products (Apricot Goji & Almond, Macadamia Choc Fudge Brownie, Oh MG Pistachio & Coconut) have status "Will be listed - being prepared" as a placeholder guess from the original migration — needs manual correction by the user
- Deploying a frontend change: `npm run build` rewrites `frontend/dist/index.html` to new asset names immediately, which breaks the live page until `manage.py collectstatic` + a server restart — do all three together.

## Infra
- **Tailscale**: connected under `achievecafeprovisions@gmail.com` (one shared login for the whole team)
- **Always on** (user asked 2026-09-24): Startup-folder shortcut `NPD Tracker v2 Server.lnk` → `run_server.bat` (self-restarting loop, exits if 8001 already served), plus scheduled task "NPD Tracker v2 Keep Alive" every 5 min → `keep_alive.vbs`/`keep_alive.ps1` (restarts if unresponsive; log `backend/logs/keep_alive.log`). Both tested live. Remaining gap: nothing starts until a Windows login — fix needs the user to run `schtasks /change ... /ru order /rp *` as admin (in DEPLOYMENT_NOTES.md); not done yet — first attempt failed because the user typed the Windows PIN; the Windows login `order` is a Microsoft account (orders@achievewholesale.com.au), so it needs that Microsoft account password. User deferred it ("later") on 2026-09-24. The PC is a laptop (has a battery); AC sleep = never.
- Restarting the server remotely: kill the `cmd.exe` whose command line has `NPD-Tracker-v2\run_server.bat` (tree kill), then start it via `Invoke-CimMethod Win32_Process Create` (detached, minimized)
- **Auto-deploy** (built 2026-09-24 at the user's request, so they can change code from another computer): scheduled task "NPD Tracker v2 Auto Deploy" every 5 min → `auto_deploy.vbs`/`auto_deploy.ps1`; push to `main` on GitHub and the office PC tests, builds, migrates, restarts, rolls back on failure; log `backend/logs/auto_deploy.log`. It SKIPS while the office folder has uncommitted changes or unpushed commits — so after editing on the office PC (incl. syncing `docs/memory`), always commit AND push, or auto-deploy stalls.
- **Firewall**: inbound TCP 8001 open (added manually from an elevated PowerShell — this working session has no admin rights)
- **Google Sign-In** deliberately disabled (doesn't work over raw IP addresses) — email/password only

**How to apply:** to add a staff login, use `/admin/` (Users → Add user) on the host. If the LAN or Tailscale IP changes, update `backend/.env` (`DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`) and restart. Credentials are also in `DEPLOYMENT_NOTES.md` (gitignored) in the project folder. See [[user-role-acp]] for how this user prefers infra work explained.
