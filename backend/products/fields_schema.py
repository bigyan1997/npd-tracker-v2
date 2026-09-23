"""
Single source of truth for the product form/table: field labels, sections,
UI type, and the required/dashboard/pipeline display flags. Served to the
frontend via GET /api/schema/ so the form and table stay schema-driven
(ported from v1 — same field set, same keys, same flags).

Each field's "key" matches a real column on the Product model.
"""

FIELDS = [
    {"key": "date", "label": "Date", "type": "date", "section": "Overview",
     "required": True, "dashboard": True},
    {"key": "product", "label": "ACP Product Name", "type": "text", "section": "Overview",
     "required": True, "dashboard": True, "tableLabel": "Product"},
    {
        "key": "status",
        "label": "Status",
        "type": "select",
        "section": "Overview",
        "required": True,
        "dashboard": True,
        "options": [
            "New Product - awaiting to receive",
            "New Product - to be processed",
            "Under Consideration - being processed",
            "Will be listed - being prepared",
            "Will NOT Be listed",
            "Created - waiting to go live",
            "Activated / Live",
        ],
    },
    {"key": "active", "label": "Active", "type": "yn", "section": "Overview",
     "required": True, "dashboard": True},
    {"key": "supplier", "label": "Supplier", "type": "combo", "section": "Overview",
     "required": True, "dashboard": True},

    {"key": "sampleReceived", "dashboard": True, "label": "Sample Received", "type": "date", "section": "Sampling & Tasting"},
    {"key": "dimensions", "dashboard": True, "label": "Dimensions – L x W x H (cm's)", "type": "text", "section": "Sampling & Tasting",
     "placeholder": "e.g. 12 x 8 x 4"},
    {"key": "weight", "dashboard": True, "label": "Weight (sample only — NOT NI)", "type": "text", "section": "Sampling & Tasting"},
    {"key": "imagesLocation", "label": "Photograph & Save Images — Original Images Location", "type": "text",
     "section": "Sampling & Tasting", "placeholder": "Folder / drive path"},
    {"key": "tastingNotes", "dashboard": True, "label": "Detailed Description After Tasting", "type": "textarea",
     "section": "Sampling & Tasting"},
    {"key": "supplierDescription", "dashboard": True, "label": "Description from Supplier (website / discussion)", "type": "textarea",
     "section": "Sampling & Tasting"},

    {"key": "nutritionalsReceived", "label": "Product Nutritionals Received", "type": "yn",
     "section": "Nutritionals & Compliance", "pipeline": True, "dashboard": True,
     "tableLabel": "Nutritionals", "chipLabel": "NR"},
    {"key": "nutritionalsACP", "label": "Nutritionals Created into ACP Format", "type": "yn",
     "section": "Nutritionals & Compliance", "pipeline": True, "dashboard": True,
     "tableLabel": "Nutritionals ACP", "chipLabel": "NC"},
    {"key": "shelfLife", "dashboard": True, "label": "Shelf Life of Product", "type": "text", "section": "Nutritionals & Compliance"},
    {"key": "features", "dashboard": True, "label": "Features — e.g. GF, DF, Halal", "type": "text",
     "section": "Nutritionals & Compliance"},

    {"key": "unitsPerBox", "dashboard": True, "label": "Units per Box", "type": "number", "section": "Commercial"},
    {"key": "supplierAvailableFrom", "dashboard": True, "label": "Supplier Available From Date", "type": "date", "section": "Commercial"},
    {"key": "supplierProductCode", "dashboard": True, "label": "Supplier Product Code", "type": "text", "section": "Commercial"},
    {"key": "cost", "label": "Cost", "type": "number", "section": "Commercial", "step": "0.01", "dashboard": True},
    {"key": "sellWholesale", "dashboard": True, "label": "Sell — Wholesale", "type": "number", "section": "Commercial", "step": "0.01"},
    {"key": "sellACS", "dashboard": True, "label": "Sell — ACS", "type": "number", "section": "Commercial", "step": "0.01"},
    {"key": "acpProductCode2", "dashboard": True, "label": "ACP Product Code2", "type": "text", "section": "Commercial"},
    {"key": "qblueProductName", "dashboard": True, "label": "Qblue Product Name", "type": "text", "section": "Commercial"},
    {"key": "b2bProductName", "dashboard": True, "label": "B2B Product Name", "type": "text", "section": "Commercial"},

    {"key": "loadedQblue", "label": "Created in ZeaBlue Products and Supplier Price List", "type": "yn",
     "section": "Go-to-Market Checklist", "pipeline": True, "dashboard": True,
     "tableLabel": "Price List", "chipLabel": "ZB"},
    {"key": "imgB2BNew", "label": "Image for B2B — with NEW symbol, Symbols & Watermark", "type": "yn",
     "section": "Go-to-Market Checklist", "pipeline": True, "dashboard": True,
     "tableLabel": "B2B Image (New)", "chipLabel": "BI"},
    {"key": "imgB2BNoNew", "label": "Image for B2B — Symbols & Watermark (NEW symbol removed)", "type": "yn",
     "section": "Go-to-Market Checklist", "pipeline": True, "dashboard": True,
     "tableLabel": "B2B Image", "chipLabel": "BS"},
    {"key": "imgPrint", "label": "Image for Print — Watermark removed, cut-off & dietary symbols", "type": "yn",
     "section": "Go-to-Market Checklist", "pipeline": True, "dashboard": True,
     "tableLabel": "Print Image", "chipLabel": "IW"},
    {"key": "createdB2B", "label": "Create Product into B2B", "type": "yn",
     "section": "Go-to-Market Checklist", "pipeline": True, "dashboard": True,
     "tableLabel": "In B2B", "chipLabel": "B2B"},
    {"key": "supplierProductName", "dashboard": True, "label": "Supplier product name (if different to ACP product name)",
     "type": "text", "section": "Overview"},
    {"key": "imagesNote", "dashboard": True, "label": "Note about images", "type": "text", "section": "Sampling & Tasting"},
    {"key": "plannedLaunch", "dashboard": True, "label": "Planned Launch", "type": "textarea", "section": "Overview",
     "placeholder": "e.g. target launch month, channels, promo plans"},
]

FIELDS_BY_KEY = {f["key"]: f for f in FIELDS}
SECTIONS = list(dict.fromkeys(f["section"] for f in FIELDS))
PIPELINE_FIELDS = [f for f in FIELDS if f.get("pipeline")]
DASHBOARD_FIELDS = [f for f in FIELDS if f.get("dashboard")]
REQUIRED_FIELDS = [f for f in FIELDS if f.get("required")]
FIELD_KEYS = [f["key"] for f in FIELDS]
SEARCH_KEYS = [
    "product", "supplierProductName", "supplier", "supplierProductCode", "acpProductCode2",
    "qblueProductName", "b2bProductName",
]

STATUS_CHOICES = [(opt, opt) for opt in FIELDS_BY_KEY["status"]["options"]]

# Field keys whose UI type is "yn" — stored as BooleanField on the model,
# translated to "Y"/"N" only at the CSV-export/Sheets-sync boundary.
YN_FIELD_KEYS = [f["key"] for f in FIELDS if f["type"] == "yn"]

STUCK_DAYS_THRESHOLD = 30
STUCK_EXCLUDED_STATUSES = {"Will NOT Be listed", "Activated / Live"}
