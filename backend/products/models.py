import re
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from .fields_schema import STATUS_CHOICES
from .validators import validate_image_file_size


def _slugify_for_filename(value):
    value = re.sub(r"[^A-Za-z0-9]+", "_", (value or "").strip()).strip("_")
    return value or "product"


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    # Overview
    date = models.DateField()
    product = models.CharField(max_length=255)
    status = models.CharField(max_length=64, choices=STATUS_CHOICES, blank=True)
    active = models.BooleanField(default=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="products")
    supplierProductName = models.CharField(max_length=255, blank=True)

    # Sampling & Tasting
    sampleReceived = models.DateField(null=True, blank=True)
    dimensions = models.CharField(max_length=255, blank=True)
    weight = models.CharField(max_length=255, blank=True)
    imagesLocation = models.CharField(max_length=500, blank=True)
    imagesNote = models.CharField(max_length=500, blank=True)
    tastingNotes = models.TextField(blank=True)
    supplierDescription = models.TextField(blank=True)

    # Nutritionals & Compliance
    nutritionalsReceived = models.BooleanField(default=False)
    nutritionalsACP = models.BooleanField(default=False)
    shelfLife = models.CharField(max_length=255, blank=True)
    features = models.CharField(max_length=255, blank=True)

    # Commercial
    unitsPerBox = models.PositiveIntegerField(null=True, blank=True)
    supplierAvailableFrom = models.DateField(null=True, blank=True)
    supplierProductCode = models.CharField(max_length=255, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sellWholesale = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sellACS = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    acpProductCode2 = models.CharField(max_length=255, blank=True)
    qblueProductName = models.CharField(max_length=255, blank=True)
    b2bProductName = models.CharField(max_length=255, blank=True)

    # Go-to-Market Checklist
    loadedQblue = models.BooleanField(default=False)
    imgB2BNew = models.BooleanField(default=False)
    imgB2BNoNew = models.BooleanField(default=False)
    imgPrint = models.BooleanField(default=False)
    createdB2B = models.BooleanField(default=False)

    # Tracking — replaces v1's audit-log-derived "stuck in status" query and
    # string lastEditedBy/lastEditedAt columns with real, indexed columns.
    status_changed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    sheet_row_synced_at = models.DateTimeField(null=True, blank=True)

    # Google Drive photo folders (see drive_client.py) — the product's own
    # folder plus one subfolder per image category.
    drive_folder_id = models.CharField(max_length=128, blank=True)
    drive_product_folder_id = models.CharField(max_length=128, blank=True)
    drive_nutrition_folder_id = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["active"]),
            models.Index(fields=["status_changed_at"]),
        ]

    def __str__(self):
        return self.product or f"Product #{self.pk}"


    def drive_folder_for(self, category):
        if category == ProductImage.CATEGORY_PRODUCT:
            return self.drive_product_folder_id
        return self.drive_nutrition_folder_id


def product_image_filename(product, category, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    code = "PI" if category == "product" else "NI"
    product_name = _slugify_for_filename(product.product if product else "")
    date_str = timezone.localdate().strftime("%Y%m%d")  # Sydney date, not UTC
    unique = uuid.uuid4().hex[:6]  # avoids overwriting a same-day second upload for this product/category
    return f"{product_name}_{code}_{date_str}_{unique}.{ext}"


def product_image_upload_path(instance, filename):
    folder = "product_images" if instance.category == "product" else "nutritional_images"
    product_name = _slugify_for_filename(instance.product.product if instance.product_id else "")
    product_folder = f"{product_name}_{instance.product_id}"
    name = product_image_filename(instance.product if instance.product_id else None, instance.category, filename)
    return f"{folder}/{product_folder}/{name}"


class ProductImage(models.Model):
    CATEGORY_PRODUCT = "product"
    CATEGORY_NUTRITION = "nutrition"
    CATEGORY_CHOICES = [
        (CATEGORY_PRODUCT, "Product"),
        (CATEGORY_NUTRITION, "Nutrition Label"),
    ]

    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES)
    # Local file — only used when Drive isn't configured (dev/tests).
    image = models.ImageField(
        upload_to=product_image_upload_path, validators=[validate_image_file_size], blank=True
    )
    # Drive-stored photo. Drive is the source of truth: rows are created/
    # updated/removed by drive_sync to match what's actually in the folders,
    # including photos staff dropped in directly via the Drive app.
    drive_file_id = models.CharField(max_length=128, unique=True, null=True, blank=True)
    drive_modified_at = models.DateTimeField(null=True, blank=True)
    drive_thumbnail_link = models.TextField(blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["category", "sort_order", "uploaded_at"]
