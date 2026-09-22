from django.contrib import admin

from .models import AuditLogEntry


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ["changed_at", "record_id", "product_name_snapshot", "field_key", "action", "changed_by"]
    list_filter = ["action", "changed_by"]
    search_fields = ["record_id", "field_key", "product_name_snapshot"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
