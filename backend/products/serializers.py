from django.utils import timezone
from rest_framework import serializers

from . import drive_client, fields_schema, image_files
from .models import Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    # Both served through the app (see image_files.py); `v` busts the
    # browser cache when the photo is changed in Drive.
    image = serializers.SerializerMethodField()
    thumb = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "category", "image", "thumb", "filename", "uploaded_at", "sort_order"]

    def _url(self, obj):
        return f"/api/products/{obj.product_id}/images/{obj.pk}/file/?v={image_files.version(obj)}"

    def get_image(self, obj):
        return self._url(obj)

    def get_thumb(self, obj):
        return self._url(obj) + "&size=thumb"


def photo_folders(product):
    return {
        "product": drive_client.folder_url(product.drive_product_folder_id),
        "nutrition": drive_client.folder_url(product.drive_nutrition_folder_id),
    }


class ProductImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["category", "image"]
        # The model field is blank=True (Drive-stored photos have no local
        # file), but an upload must still include one.
        extra_kwargs = {"image": {"required": True, "allow_null": False}}


class ProductSerializer(serializers.ModelSerializer):
    supplier = serializers.CharField(source="supplier.name", read_only=True)
    lastEditedBy = serializers.SerializerMethodField()
    lastEditedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    stuck = serializers.SerializerMethodField()
    daysInStatus = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    photoFolders = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = fields_schema.FIELD_KEYS + [
            "id", "lastEditedBy", "lastEditedAt", "stuck", "daysInStatus", "images", "photoFolders",
        ]

    def get_photoFolders(self, obj):
        return photo_folders(obj)

    def get_lastEditedBy(self, obj):
        return obj.last_edited_by.get_username() if obj.last_edited_by else ""

    def get_daysInStatus(self, obj):
        return (timezone.now() - obj.status_changed_at).days

    def get_stuck(self, obj):
        if obj.status in fields_schema.STUCK_EXCLUDED_STATUSES:
            return False
        return self.get_daysInStatus(obj) >= fields_schema.STUCK_DAYS_THRESHOLD
