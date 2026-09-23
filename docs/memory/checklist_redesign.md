---
name: checklist-redesign
description: Proposed (not built) redesign of the Go-to-Market checklist UI in NPD v2 — waiting on user to confirm step order and whether the two B2B image steps are sequential
metadata:
  type: project
---

On 2026-09-24 I proposed replacing the table's cryptic chips (NR NC ZB BI BS IW B2B, names only on mouse hover — broken on touch devices) with one progress column (`▰▰▰▰▱▱▱ 4/7 · Next: Print image`, tap/hover for the named list, sortable), and replacing the edit form's YES/NO pairs for the 7 `pipeline` fields with a dedicated vertical tick-box "Go-to-Market Checklist" card in workflow order. No data migration — same boolean fields; only an order hint in `fields_schema.py`. Later idea: show who/when ticked each item from the audit log.

**Status:** user said "leave it here, I'll confirm and let you know". Blocking questions: (1) is the order NR → NC → ZB → BI → BS → IW → B2B the real workflow order? (2) are the two "Image for B2B" steps (with NEW symbol / NEW symbol removed) sequential or either/or (either/or means 7/7 can't be reached)?

**How to apply:** when the user returns to this, don't re-propose — ask for / use their answers and build it. Related: [[npd-tracker-deployment]].

**Also fold in when building:** warn when "Product Nutritionals Received" is ticked but the product has no nutrition-label photo (agreed 2026-09-24 to add this with the checklist work). Photo count column/filter/empty-gallery hints were already built on 2026-09-24 with no minimum rule (only categories with zero photos are flagged) — user never gave a minimum; ask if they want one.
