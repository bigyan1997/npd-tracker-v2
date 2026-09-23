---
name: user-role-acp
description: "User manages operational tooling for Achieve Cafe Provisions, not a professional developer — needs infra steps walked through, not just handed"
metadata: 
  type: user
---

The user runs operations/admin for Achieve Cafe Provisions, a food supplier/provisions business, and is not a professional developer. They direct work at a high level ("make this work", "populate the data from here") rather than specifying technical details, and rely on being walked through external consoles (e.g. Google Cloud Console service account creation) step by step rather than being handed a command to run unsupervised.

**Why:** observed while setting up [[npd-tracker-deployment]] — the user needed guided steps for Google Cloud service account creation and Tailscale sign-in (both requiring interactive browser steps only they could complete), and answered infra questions (host machine, credentials) in short, sometimes informal/typo'd messages.

**How to apply:** favor concrete step-by-step instructions over jargon when a manual/external step is required; confirm before installing software or changing system state; keep explanations plain and skip assuming familiarity with dev tooling (git, venv, npm, etc.).
