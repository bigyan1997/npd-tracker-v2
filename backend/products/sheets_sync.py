"""
One-way Postgres -> Google Sheets mirror. Postgres is the real source of
truth (see fields_schema.py / services.py); this sheet exists so the team
can still glance at a familiar spreadsheet. Every function here is
best-effort: it must never raise, and it must never block or roll back the
Postgres write that triggered it. Call these only after the real write has
already committed.

The actual Sheets API calls run on a background thread — a single push is
~3s of network round trips (Google Sheets API, not local), which is way too
slow to make a Save/Delete click wait on. `push_product`/`push_delete`
return immediately; `_push_product_sync`/`_push_delete_sync` do the real
work off-thread.
"""

import logging
import threading

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from . import drive_client
from .sheets_client import SheetsClient

logger = logging.getLogger(__name__)

# Set once the tab/header has been confirmed to exist in this process, so we
# stop re-checking on every single save (it was previously 2 extra API calls
# per save, almost always confirming something already true).
_header_ensured = False


def _configured():
    return bool(settings.NPD_SHEET_ID)


def _record_from_snapshot(product_id, snapshot):
    record = {"_id": str(product_id), **snapshot}
    record["lastEditedBy"] = ""
    record["lastEditedAt"] = timezone.localtime().strftime("%Y-%m-%d %H:%M")  # Sydney time
    return record


def _run_in_background(target, *args):
    def runner():
        try:
            target(*args)
        finally:
            # This thread isn't managed by Django's request lifecycle, so
            # nothing else closes the DB connection it opened.
            close_old_connections()

    threading.Thread(target=runner, daemon=True).start()


def push_product(product, snapshot):
    """snapshot: the same FIELD_KEYS -> string dict services._snapshot_dict
    produces. Passed in rather than recomputed so callers don't need to
    import services (avoids a circular import) and so the mirrored row
    matches exactly what was just saved."""
    if not _configured():
        return
    _run_in_background(_push_product_sync, product, snapshot)


def _push_product_sync(product, snapshot):
    global _header_ensured
    try:
        client = SheetsClient()
        if not _header_ensured:
            client.ensure_tab_and_header()
            _header_ensured = True
        record = _record_from_snapshot(product.pk, snapshot)
        if product.last_edited_by:
            record["lastEditedBy"] = product.last_edited_by.get_username()
        from .models import Product  # local import to avoid a module-load cycle

        # The photos column links to the product's Drive folder once it has
        # one (read fresh: the folder may have been created after `product`
        # was loaded). The typed legacy path stays in Postgres untouched.
        folder_id = Product.objects.filter(pk=product.pk).values_list("drive_folder_id", flat=True).first()
        if folder_id:
            record["imagesLocation"] = drive_client.folder_url(folder_id)
        row_number = client.find_row_by_record_id(product.pk)
        if row_number:
            client.update_row(row_number, record)
        else:
            client.append_row(record)
        Product.objects.filter(pk=product.pk).update(sheet_row_synced_at=timezone.now())
    except Exception:
        logger.exception("Sheets push failed for product %s", product.pk)


def push_delete(product_id):
    if not _configured():
        return
    _run_in_background(_push_delete_sync, product_id)


def _push_delete_sync(product_id):
    try:
        client = SheetsClient()
        row_number = client.find_row_by_record_id(product_id)
        if row_number:
            client.delete_row(row_number)
    except Exception:
        logger.exception("Sheets delete-push failed for product %s", product_id)
