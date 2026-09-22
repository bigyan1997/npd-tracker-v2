from django.contrib import admin

from .models import Product, ProductImage, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ["category", "image", "sort_order", "uploaded_by", "uploaded_at"]
    readonly_fields = ["uploaded_by", "uploaded_at"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["product", "supplier", "status", "active", "date", "status_changed_at"]
    list_filter = ["status", "active"]
    search_fields = ["product", "supplierProductName", "supplierProductCode", "acpProductCode2"]
    inlines = [ProductImageInline]
