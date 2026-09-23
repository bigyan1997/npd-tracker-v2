import json
from datetime import date

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from audit.models import AuditLogEntry

from . import drive_sync, fields_schema, sheets_sync
from .models import Product, Supplier


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    """The product changed since the client loaded it — saving would silently
    overwrite someone else's edit. Everyone shares one login, so this is the
    only way to tell two people's edits apart."""


def _validate_required(data):
    missing = []
    for field in fields_schema.REQUIRED_FIELDS:
        value = data.get(field["key"])
        if value in (None, ""):
            missing.append(field["label"])
    if missing:
        verb = "is" if len(missing) == 1 else "are"
        raise ValidationError(f"{', '.join(missing)} {verb} required.")


def _validate_numeric(data):
    bad = []
    for field in fields_schema.FIELDS:
        if field["type"] != "number":
            continue
        value = data.get(field["key"])
        if value in (None, ""):
            continue
        try:
            float(value)
        except (TypeError, ValueError):
            bad.append(field["label"])
    if bad:
        raise ValidationError(f"{', '.join(bad)} must be a number.")


def _to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("y", "yes", "true", "1")


def _resolve_supplier(name):
    name = (name or "").strip()
    if not name:
        return None
    supplier, _ = Supplier.objects.get_or_create(name__iexact=name, defaults={"name": name})
    return supplier


def _apply_fields(product, data):
    for field in fields_schema.FIELDS:
        key = field["key"]
        if key == "supplier" or key not in data:
            continue
        value = data[key]
        if field["type"] == "yn":
            setattr(product, key, _to_bool(value))
        elif field["type"] == "date":
            if not value:
                setattr(product, key, None)
            elif isinstance(value, str):
                try:
                    setattr(product, key, date.fromisoformat(value))
                except ValueError:
                    raise ValidationError(f"{field['label']} must be a valid date (YYYY-MM-DD).")
            else:
                setattr(product, key, value)
        elif field["type"] == "number":
            setattr(product, key, value if value not in (None, "") else None)
        else:
            setattr(product, key, value or "")


def _field_label(key):
    field = fields_schema.FIELDS_BY_KEY.get(key)
    return field["label"] if field else key


def _snapshot_dict(product):
    """Field-key -> string-ish value, in the same shape create_product's
    `data` argument expects — used for both human-readable audit entries
    and the JSON restore snapshot."""
    snapshot = {}
    for field in fields_schema.FIELDS:
        key = field["key"]
        if key == "supplier":
            snapshot[key] = product.supplier.name if product.supplier_id else ""
            continue
        value = getattr(product, key)
        if field["type"] == "yn":
            snapshot[key] = "Y" if value else "N"
        elif field["type"] == "date":
            snapshot[key] = value.isoformat() if value else ""
        elif value is None:
            snapshot[key] = ""
        else:
            snapshot[key] = str(value)
    return snapshot


def list_products(search="", status="", active=""):
    qs = Product.objects.select_related("supplier").prefetch_related("images")
    if status:
        qs = qs.filter(status=status)
    if active in ("Y", "N"):
        qs = qs.filter(active=(active == "Y"))
    if search:
        q = Q()
        for key in fields_schema.SEARCH_KEYS:
            lookup = "supplier__name__icontains" if key == "supplier" else f"{key}__icontains"
            q |= Q(**{lookup: search})
        qs = qs.filter(q)
    return qs


def get_product(pk):
    try:
        return Product.objects.select_related("supplier").prefetch_related("images").get(pk=pk)
    except Product.DoesNotExist:
        raise NotFoundError(f"Product {pk} not found.")


def create_product(data, user):
    _validate_required(data)
    _validate_numeric(data)
    supplier = _resolve_supplier(data.get("supplier"))
    if supplier is None:
        raise ValidationError("Supplier is required.")
    now = timezone.now()
    product = Product(status_changed_at=now, last_edited_by=user, supplier=supplier)
    _apply_fields(product, data)
    product.save()

    snapshot = _snapshot_dict(product)
    entries = [
        AuditLogEntry(
            product=product,
            record_id=product.pk,
            product_name_snapshot=snapshot.get("product", ""),
            field_key=key,
            field_label=_field_label(key),
            old_value="",
            new_value=value,
            action="create",
            changed_by=user,
        )
        for key, value in snapshot.items()
        if value != ""
    ]
    AuditLogEntry.objects.bulk_create(entries)
    transaction.on_commit(lambda: sheets_sync.push_product(product, snapshot))
    transaction.on_commit(lambda: drive_sync.refresh_folders_soon(product.pk))
    return product


def update_product(pk, data, user):
    product = get_product(pk)
    # Optional: omitted by "Save mine anyway", which deliberately overwrites.
    expected = parse_datetime(str(data.get("expectedUpdatedAt") or ""))
    if expected and expected != product.updated_at:
        raise ConflictError(
            "This product was changed by someone else while you had it open. "
            "Your changes haven't been saved yet."
        )
    before = _snapshot_dict(product)

    _validate_required(data)
    _validate_numeric(data)
    supplier = _resolve_supplier(data.get("supplier"))
    if supplier is None:
        raise ValidationError("Supplier is required.")
    new_status = data.get("status", product.status)
    if new_status != product.status:
        product.status_changed_at = timezone.now()
    product.supplier = supplier
    _apply_fields(product, data)
    product.last_edited_by = user
    product.save()

    after = _snapshot_dict(product)
    entries = [
        AuditLogEntry(
            product=product,
            record_id=product.pk,
            product_name_snapshot=after.get("product", ""),
            field_key=key,
            field_label=_field_label(key),
            old_value=before.get(key, ""),
            new_value=new_value,
            action="update",
            changed_by=user,
        )
        for key, new_value in after.items()
        if before.get(key, "") != new_value
    ]
    AuditLogEntry.objects.bulk_create(entries)
    transaction.on_commit(lambda: sheets_sync.push_product(product, after))
    if before.get("product") != after.get("product"):
        transaction.on_commit(lambda: drive_sync.refresh_folders_soon(product.pk))
    return product


def delete_product(pk, user):
    product = get_product(pk)
    snapshot = _snapshot_dict(product)
    AuditLogEntry.objects.create(
        product=product,
        record_id=product.pk,
        product_name_snapshot=snapshot.get("product", ""),
        field_key="__deleted__",
        field_label="Deleted product",
        old_value=json.dumps(snapshot),
        new_value="",
        action="delete",
        changed_by=user,
    )
    product_id = product.pk
    drive_folder_id = product.drive_folder_id
    product.delete()
    transaction.on_commit(lambda: sheets_sync.push_delete(product_id))
    transaction.on_commit(lambda: drive_sync.trash_folder(drive_folder_id))


def product_history(pk):
    return AuditLogEntry.objects.filter(record_id=pk).order_by("-changed_at")


def list_recent_deletions(limit=20):
    return AuditLogEntry.objects.filter(action="delete").order_by("-changed_at")[:limit]


def restore_product(audit_id, user):
    try:
        entry = AuditLogEntry.objects.get(id=audit_id, action="delete")
    except AuditLogEntry.DoesNotExist:
        raise NotFoundError(f"No deleted-product record with id {audit_id}")
    try:
        snapshot = json.loads(entry.old_value)
    except (TypeError, ValueError):
        raise ValidationError("This deletion record can't be restored (unreadable snapshot).")
    data = {key: snapshot.get(key, "") for key in fields_schema.FIELD_KEYS}
    return create_product(data, user)


def import_products(rows, user):
    """Bulk create via create_product (reuses its validation/audit/
    status_changed_at logic). Unlike v1's Sheets-backed version, a row that
    fails validation (not just a blank product name) is skipped rather than
    crashing the whole import — real Postgres columns reject bad data that
    untyped Sheets cells would have silently accepted."""
    imported = []
    skipped = 0
    for row in rows:
        if not (row.get("product") or "").strip():
            skipped += 1
            continue
        try:
            imported.append(create_product(row, user))
        except ValidationError:
            skipped += 1
    return imported, skipped


def list_supplier_names():
    return list(Supplier.objects.values_list("name", flat=True))


def create_supplier(name):
    name = (name or "").strip()
    if not name:
        raise ValidationError("Supplier name is required.")
    Supplier.objects.get_or_create(name__iexact=name, defaults={"name": name})
    return list_supplier_names()


def rename_supplier(name, new_name, user):
    """Rename a supplier everywhere: products point at the Supplier row, so
    they all follow automatically. Each affected product gets a History
    entry and is re-pushed to the Sheets mirror (which stores the name)."""
    name = (name or "").strip()
    new_name = (new_name or "").strip()
    if not name or not new_name:
        raise ValidationError("Supplier name is required.")
    try:
        supplier = Supplier.objects.get(name__iexact=name)
    except Supplier.DoesNotExist:
        raise ValidationError(f'"{name}" is not in the supplier list.')
    if new_name == supplier.name:
        return list_supplier_names()
    clash = Supplier.objects.filter(name__iexact=new_name).exclude(pk=supplier.pk).first()
    if clash:
        raise ValidationError(f'"{clash.name}" is already in the supplier list.')

    old_name = supplier.name
    with transaction.atomic():
        supplier.name = new_name
        supplier.save(update_fields=["name"])
        # Counts as a change to each product, so a form opened before the
        # rename can't save the old name back (see ConflictError).
        Product.objects.filter(supplier=supplier).update(updated_at=timezone.now())
        products = list(Product.objects.filter(supplier=supplier).select_related("supplier"))
        AuditLogEntry.objects.bulk_create([
            AuditLogEntry(
                product=product,
                record_id=product.pk,
                product_name_snapshot=product.product,
                field_key="supplier",
                field_label=_field_label("supplier"),
                old_value=old_name,
                new_value=new_name,
                action="update",
                changed_by=user,
            )
            for product in products
        ])
        for product in products:
            snapshot = _snapshot_dict(product)
            transaction.on_commit(lambda p=product, s=snapshot: sheets_sync.push_product(p, s))
    return list_supplier_names()


def delete_supplier(name):
    name = (name or "").strip()
    if not name:
        raise ValidationError("Supplier name is required.")
    try:
        supplier = Supplier.objects.get(name__iexact=name)
    except Supplier.DoesNotExist:
        return list_supplier_names()
    in_use = Product.objects.filter(supplier=supplier).count()
    if in_use:
        raise ValidationError(
            f'"{name}" is still used by {in_use} product{"s" if in_use != 1 else ""} and can\'t be deleted.'
        )
    supplier.delete()
    return list_supplier_names()
