from django.utils import timezone
from rest_framework import serializers

from . import fields_schema
from .models import Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "category", "image", "uploaded_at", "sort_order"]


class ProductImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["category", "image"]


class ProductSerializer(serializers.ModelSerializer):
    supplier = serializers.CharField(source="supplier.name", read_only=True)
    lastEditedBy = serializers.SerializerMethodField()
    lastEditedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    stuck = serializers.SerializerMethodField()
    daysInStatus = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = fields_schema.FIELD_KEYS + [
            "id", "lastEditedBy", "lastEditedAt", "stuck", "daysInStatus", "images",
        ]

    def get_lastEditedBy(self, obj):
        return obj.last_edited_by.get_username() if obj.last_edited_by else ""

    def get_daysInStatus(self, obj):
        return (timezone.now() - obj.status_changed_at).days

    def get_stuck(self, obj):
        if obj.status in fields_schema.STUCK_EXCLUDED_STATUSES:
            return False
        return self.get_daysInStatus(obj) >= fields_schema.STUCK_DAYS_THRESHOLD
