"""
One-way Postgres -> Google Sheets mirror. Postgres is the real source of
truth (see fields_schema.py / services.py); this sheet exists so the team
can still glance at a familiar spreadsheet. Every function here is
best-effort: it must never raise, and it must never block or roll back the
Postgres write that triggered it. Call these only after the real write has
already committed.
"""

import logging

from django.conf import settings
from django.utils import timezone

from .sheets_client import SheetsClient

logger = logging.getLogger(__name__)


def _configured():
    return bool(settings.NPD_SHEET_ID)


def _record_from_snapshot(product_id, snapshot):
    record = {"_id": str(product_id), **snapshot}
    record["lastEditedBy"] = ""
    record["lastEditedAt"] = timezone.now().isoformat()
    return record


def push_product(product, snapshot):
    """snapshot: the same FIELD_KEYS -> string dict services._snapshot_dict
    produces. Passed in rather than recomputed so callers don't need to
    import services (avoids a circular import) and so the mirrored row
    matches exactly what was just saved."""
    if not _configured():
        return
    try:
        client = SheetsClient()
        client.ensure_tab_and_header()
        record = _record_from_snapshot(product.pk, snapshot)
        if product.last_edited_by:
            record["lastEditedBy"] = product.last_edited_by.get_username()
        row_number = client.find_row_by_record_id(product.pk)
        if row_number:
            client.update_row(row_number, record)
        else:
            client.append_row(record)
        from .models import Product  # local import to avoid a module-load cycle

        Product.objects.filter(pk=product.pk).update(sheet_row_synced_at=timezone.now())
    except Exception:
        logger.exception("Sheets push failed for product %s", product.pk)


def push_delete(product_id):
    if not _configured():
        return
    try:
        client = SheetsClient()
        row_number = client.find_row_by_record_id(product_id)
        if row_number:
            client.delete_row(row_number)
    except Exception:
        logger.exception("Sheets delete-push failed for product %s", product_id)
