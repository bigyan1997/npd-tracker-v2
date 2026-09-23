import logging
import mimetypes
import re

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import drive_client, drive_sync, image_files, import_parser, services
from .drive_client import DriveClient
from .models import ProductImage, product_image_filename
from .serializers import (
    ProductImageSerializer,
    ProductImageUploadSerializer,
    ProductSerializer,
    photo_folders,
)

logger = logging.getLogger(__name__)

DRIVE_UNAVAILABLE = "Couldn't reach Google Drive. Please try again in a moment."


class ProductViewSet(viewsets.ViewSet):
    def list(self, request):
        rows = services.list_products(
            search=request.query_params.get("search", ""),
            status=request.query_params.get("status", ""),
            active=request.query_params.get("active", ""),
        )
        return Response(ProductSerializer(rows, many=True).data)

    def retrieve(self, request, pk=None):
        try:
            product = services.get_product(pk)
        except services.NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductSerializer(product).data)

    def create(self, request):
        try:
            product = services.create_product(request.data, request.user)
        except services.ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        try:
            product = services.update_product(pk, request.data, request.user)
        except services.ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except services.NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except services.ConflictError as exc:
            return Response({"detail": str(exc), "conflict": True}, status=status.HTTP_409_CONFLICT)
        return Response(ProductSerializer(product).data)

    def partial_update(self, request, pk=None):
        return self.update(request, pk=pk)

    def destroy(self, request, pk=None):
        try:
            services.delete_product(pk, request.user)
        except services.NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="import/preview")
    def import_preview(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rows, unmapped_columns = import_parser.parse_csv(file)
        except import_parser.ParseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"rows": rows, "unmappedColumns": unmapped_columns})

    @action(detail=False, methods=["post"], url_path="import/commit")
    def import_commit(self, request):
        rows = request.data.get("rows", [])
        row_data = [r.get("data", {}) for r in rows]
        records, skipped = services.import_products(row_data, request.user)
        if not records:
            return Response({"detail": "No valid rows to import."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"imported": len(records), "skipped": skipped}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        entries = services.product_history(pk)
        return Response([
            {
                "fieldLabel": e.field_label,
                "oldValue": e.old_value,
                "newValue": e.new_value,
                "action": e.action,
                "changedBy": e.changed_by.get_username() if e.changed_by else "",
                "changedAt": e.changed_at.isoformat(),
            }
            for e in entries
        ])


class DeletedProductsView(APIView):
    def get(self, request):
        entries = services.list_recent_deletions()
        return Response([
            {
                "auditId": e.id,
                "productName": e.product_name_snapshot,
                "deletedBy": e.changed_by.get_username() if e.changed_by else "",
                "deletedAt": e.changed_at.isoformat(),
            }
            for e in entries
        ])


class RestoreProductView(APIView):
    def post(self, request, pk=None):
        try:
            product = services.restore_product(pk, request.user)
        except services.NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except services.ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


class ProductImageUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk=None):
        """The product's photos, freshly pulled from Drive first — picks up
        anything staff added/removed directly in the Drive app."""
        try:
            product = services.get_product(pk)
        except services.NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        if drive_client.enabled():
            try:
                drive_sync.sync_product(product)
            except Exception:
                # Still show what we already know rather than nothing.
                logger.exception("Drive sync failed for product %s", pk)
        images = ProductImage.objects.filter(product=product)
        return Response({
            "images": ProductImageSerializer(images, many=True).data,
            "photoFolders": photo_folders(product),
        })

    def post(self, request, pk=None):
        try:
            product = services.get_product(pk)
        except services.NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response({"detail": str(first_error)}, status=status.HTTP_400_BAD_REQUEST)
        if not drive_client.enabled():
            image = serializer.save(product=product, uploaded_by=request.user)
            return Response(ProductImageSerializer(image).data, status=status.HTTP_201_CREATED)

        category = serializer.validated_data["category"]
        upload = serializer.validated_data["image"]
        upload.seek(0)
        mime = upload.content_type or mimetypes.guess_type(upload.name)[0] or "application/octet-stream"
        try:
            client = DriveClient()
            drive_sync.ensure_folders(product, client, verify=True)
            meta = client.upload(
                product.drive_folder_for(category),
                product_image_filename(product, category, upload.name),
                upload.read(),
                mime,
            )
        except Exception:
            logger.exception("Drive upload failed for product %s", pk)
            return Response({"detail": DRIVE_UNAVAILABLE}, status=status.HTTP_502_BAD_GATEWAY)
        image = drive_sync.upsert_from_drive(product, category, meta, uploaded_by=request.user)
        return Response(ProductImageSerializer(image).data, status=status.HTTP_201_CREATED)


class ProductImageDeleteView(APIView):
    def delete(self, request, pk=None, image_id=None):
        try:
            image = ProductImage.objects.get(pk=image_id, product_id=pk)
        except ProductImage.DoesNotExist:
            return Response({"detail": "Image not found."}, status=status.HTTP_404_NOT_FOUND)
        if image.drive_file_id:
            try:
                DriveClient().trash(image.drive_file_id)
            except Exception:
                logger.exception("Drive trash failed for image %s", image.pk)
                return Response({"detail": DRIVE_UNAVAILABLE}, status=status.HTTP_502_BAD_GATEWAY)
        elif image.image:
            image.image.delete(save=False)
        image_files.clear_cached(image)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageFileView(APIView):
    """The photo itself (or its gallery thumbnail with ?size=thumb)."""

    def get(self, request, pk=None, image_id=None):
        try:
            image = ProductImage.objects.get(pk=image_id, product_id=pk)
        except ProductImage.DoesNotExist:
            return Response({"detail": "Image not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            if request.query_params.get("size") == "thumb":
                data, content_type = image_files.thumbnail(image)
            else:
                data, content_type = image_files.full(image)
        except Exception:
            logger.exception("Couldn't load image %s", image.pk)
            return Response({"detail": DRIVE_UNAVAILABLE}, status=status.HTTP_502_BAD_GATEWAY)
        response = HttpResponse(data, content_type=content_type)
        if content_type == "application/pdf":
            # Open in the browser's PDF viewer rather than downloading.
            name = re.sub(r'[^A-Za-z0-9._-]', "_", image.filename or "nutrition-label.pdf")
            response["Content-Disposition"] = f'inline; filename="{name}"'
        # URLs carry ?v=<modified time>, so a changed photo gets a new URL.
        response["Cache-Control"] = "private, max-age=604800"
        return response


class AppVersionView(APIView):
    """Identifies the frontend build currently being served, so open pages
    can notice a new version and offer to reload. The built index.html
    references a content-hashed script name, which changes on every build."""

    def get(self, request):
        index = settings.FRONTEND_DIST / "index.html"
        try:
            match = re.search(r"assets/(index-[^\"]+\.js)", index.read_text(encoding="utf-8"))
        except OSError:
            match = None
        return Response({"version": match.group(1) if match else None})


class QuickLinksView(APIView):
    """Header shortcuts: the Google Sheet mirror and the Drive photos folder."""

    def get(self, request):
        sheet = (
            f"https://docs.google.com/spreadsheets/d/{settings.NPD_SHEET_ID}/edit"
            if settings.NPD_SHEET_ID
            else None
        )
        photos = None
        if drive_client.enabled():
            try:
                photos = drive_client.folder_url(DriveClient().root_folder_id())
            except Exception:
                logger.exception("Couldn't look up the Drive photos folder")
        return Response({"sheet": sheet, "photos": photos})


class SuppliersView(APIView):
    def get(self, request):
        return Response(services.list_supplier_names())

    def post(self, request):
        try:
            names = services.create_supplier(request.data.get("name", ""))
        except services.ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(names, status=status.HTTP_201_CREATED)

    def patch(self, request):
        try:
            names = services.rename_supplier(
                request.data.get("name", ""), request.data.get("newName", ""), request.user
            )
        except services.ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(names)

    def delete(self, request):
        try:
            names = services.delete_supplier(request.data.get("name", ""))
        except services.ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(names)
