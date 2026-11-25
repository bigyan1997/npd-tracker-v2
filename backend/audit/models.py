from django.conf import settings
from django.db import models


class AuditLogEntry(models.Model):
    ACTIONS = [("create", "Create"), ("update", "Update"), ("delete", "Delete")]

    # record_id/product_name_snapshot are plain values, not just the FK below,
    # so a product's history survives the product itself being deleted.
    product = models.ForeignKey(
        "products.Product", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    record_id = models.IntegerField(db_index=True)
    product_name_snapshot = models.CharField(max_length=255, blank=True)
    field_key = models.CharField(max_length=64)
    field_label = models.CharField(max_length=255, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    action = models.CharField(max_length=10, choices=ACTIONS)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    # Who actually made the change — everyone shares one login (changed_by).
    staff_name = models.CharField(max_length=100, blank=True, default="")
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    @property
    def editor(self):
        return self.staff_name or (self.changed_by.get_username() if self.changed_by else "")

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.action} {self.field_key} on record {self.record_id}"
