from django.utils import timezone
from PIL import Image
from rest_framework import serializers

from . import drive_client, fields_schema, image_files
from .models import Product, ProductImage
from .validators import MAX_IMAGE_SIZE_BYTES


class ProductImageSerializer(serializers.ModelSerializer):
    # Both served through the app (see image_files.py); `v` busts the
    # browser cache when the photo is changed in Drive.
    image = serializers.SerializerMethodField()
    thumb = serializers.SerializerMethodField()

    isPdf = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "category", "image", "thumb", "filename", "isPdf", "uploaded_at", "sort_order"]

    def get_isPdf(self, obj):
        return obj.mime_type == "application/pdf" or (obj.filename or obj.image.name or "").lower().endswith(".pdf")

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
    # A plain file field (checked in validate), not ImageField: nutrition
    # labels can also be PDFs — suppliers often send them that way.
    image = serializers.FileField()

    class Meta:
        model = ProductImage
        fields = ["category", "image"]

    def validate(self, attrs):
        upload = attrs["image"]
        if upload.size > MAX_IMAGE_SIZE_BYTES:
            raise serializers.ValidationError({"image": "Files must be 10MB or smaller."})
        is_pdf = upload.read(5) == b"%PDF-"  # the file's contents, not its name
        upload.seek(0)
        if is_pdf:
            if attrs["category"] != ProductImage.CATEGORY_NUTRITION:
                raise serializers.ValidationError({"image": "PDFs can only be added as nutrition labels."})
            return attrs
        try:
            Image.open(upload).verify()
        except Exception:
            raise serializers.ValidationError(
                {"image": "That file isn't a photo (JPG, PNG…) — or, for nutrition labels, a PDF."}
            )
        finally:
            upload.seek(0)
        return attrs


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
