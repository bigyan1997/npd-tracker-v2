"""
Keeps ProductImage rows matching what's actually in each product's Google
Drive folders. Drive is the source of truth for photos — staff add, rename,
move and delete them directly in the Drive app as well as through ours.

- `ensure_folders` creates a product's folder tree on demand.
- `sync_product` pulls one product's current Drive listing into Postgres
  (called when a product's photos are opened, so what you see is fresh).
- A background thread (`start_background_sync`, started from wsgi.py so it
  only runs in the real server, not in manage.py commands) re-syncs every
  product every NPD_DRIVE_SYNC_SECONDS and pushes folder renames/trashes.

Like sheets_sync, the background pieces are best-effort: they log and carry
on rather than raise.
"""

import logging
import threading
import time

from django.conf import settings
from django.db import close_old_connections

from . import drive_client
from .drive_client import SUBFOLDER_NAMES, DriveClient
from .models import Product, ProductImage

logger = logging.getLogger(__name__)

# Serialises ProductImage upserts: the background sync and an in-request
# upload can both see the same new Drive file at once.
_db_lock = threading.Lock()
# Stops the background pass and a request both creating folders for the
# same new product (which would leave a duplicate empty folder in Drive).
_folder_lock = threading.RLock()
_started = False


def product_folder_name(product):
    return (product.product or "").strip() or f"Product #{product.pk}"


def ensure_folders(product, client=None, verify=False):
    """Make sure the product's Drive folder + both category subfolders exist,
    storing their ids. `verify` re-checks stored ids still exist (someone
    may have deleted the folder in Drive) — worth the extra API call before
    an upload, not on every background pass."""
    client = client or DriveClient()
    with _folder_lock:
        product.refresh_from_db(
            fields=["drive_folder_id", "drive_product_folder_id", "drive_nutrition_folder_id"]
        )
        return _ensure_folders_locked(product, client, verify)


def _ensure_folders_locked(product, client, verify):
    ids = {
        "drive_folder_id": product.drive_folder_id,
        "drive_product_folder_id": product.drive_product_folder_id,
        "drive_nutrition_folder_id": product.drive_nutrition_folder_id,
    }
    if verify:
        ids = {k: (v if client.folder_is_live(v) else "") for k, v in ids.items()}
    if all(ids.values()):
        return product

    if not ids["drive_folder_id"]:
        # Always create rather than look up by name: two products can share
        # a name, and each must get its own folder.
        ids["drive_folder_id"] = client.create_folder(product_folder_name(product), client.root_folder_id())
        ids["drive_product_folder_id"] = ids["drive_nutrition_folder_id"] = ""
    parent = ids["drive_folder_id"]
    for category, field in (("product", "drive_product_folder_id"), ("nutrition", "drive_nutrition_folder_id")):
        if not ids[field]:
            ids[field] = client.get_or_create_folder(SUBFOLDER_NAMES[category], parent)

    Product.objects.filter(pk=product.pk).update(**ids)
    for k, v in ids.items():
        setattr(product, k, v)
    return product


def upsert_from_drive(product, category, meta, uploaded_by=None):
    fields = {
        "product": product,
        "category": category,
        "filename": meta["name"],
        "mime_type": meta.get("mimeType", ""),
        "drive_modified_at": drive_client.parse_time(meta.get("modifiedTime")),
        "drive_thumbnail_link": meta.get("thumbnailLink", ""),
    }
    with _db_lock:
        image, created = ProductImage.objects.get_or_create(
            drive_file_id=meta["id"],
            defaults={
                **fields,
                "uploaded_by": uploaded_by,
                "uploaded_at": drive_client.parse_time(meta.get("createdTime")),
            },
        )
        if not created:
            for k, v in fields.items():
                setattr(image, k, v)
            image.save()
    return image


def sync_product(product, client=None):
    if not (product.drive_product_folder_id or product.drive_nutrition_folder_id):
        return
    client = client or DriveClient()
    category_by_folder = {
        product.drive_product_folder_id: ProductImage.CATEGORY_PRODUCT,
        product.drive_nutrition_folder_id: ProductImage.CATEGORY_NUTRITION,
    }
    files = client.list_images(list(category_by_folder))
    seen = set()
    for meta in files:
        category = next((category_by_folder[p] for p in meta.get("parents", []) if p in category_by_folder), None)
        if category:
            upsert_from_drive(product, category, meta)
            seen.add(meta["id"])
    with _db_lock:
        # Gone from this product's folders = deleted, trashed, or moved to
        # another product (in which case that product's sync re-adds it).
        (
            ProductImage.objects.filter(product=product, drive_file_id__isnull=False)
            .exclude(drive_file_id__in=seen)
            .delete()
        )


def sync_all():
    client = DriveClient()
    for product in Product.objects.all():
        try:
            ensure_folders(product, client)
            _sync_folder_name(product, client)
            sync_product(product, client)
        except Exception:
            logger.exception("Drive sync failed for product %s", product.pk)


# Product name -> Drive folder name, as last pushed by this process. Seeded
# lazily, so a restart re-pushes each name once (a cheap no-op rename).
_pushed_names = {}


def _sync_folder_name(product, client):
    name = product_folder_name(product)
    if product.drive_folder_id and _pushed_names.get(product.pk) != name:
        client.rename(product.drive_folder_id, name)
        _pushed_names[product.pk] = name


def refresh_folders_soon(product_id):
    """After a product is created/renamed: create or rename its Drive folder
    right away (background), rather than waiting for the next sync pass —
    so staff see the folder in Drive immediately."""
    if not drive_client.enabled():
        return

    def run():
        try:
            product = Product.objects.get(pk=product_id)
            client = DriveClient()
            ensure_folders(product, client)
            _sync_folder_name(product, client)
        except Exception:
            logger.exception("Drive folder refresh failed for product %s", product_id)
        finally:
            close_old_connections()

    threading.Thread(target=run, daemon=True).start()


def trash_folder(folder_id):
    """Product deleted — send its photo folder to Drive's Bin (recoverable
    there for 30 days). Background, best-effort."""
    if not (folder_id and drive_client.enabled()):
        return

    def run():
        try:
            DriveClient().trash(folder_id)
        except Exception:
            logger.exception("Drive trash failed for folder %s", folder_id)

    threading.Thread(target=run, daemon=True).start()


def start_background_sync():
    global _started
    if _started or not drive_client.enabled():
        return
    _started = True

    def loop():
        while True:
            try:
                sync_all()
            except Exception:
                logger.exception("Drive background sync failed")
            finally:
                close_old_connections()
            time.sleep(settings.NPD_DRIVE_SYNC_SECONDS)

    threading.Thread(target=loop, daemon=True, name="drive-sync").start()
