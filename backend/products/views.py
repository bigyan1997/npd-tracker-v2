from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import import_parser, services
from .models import ProductImage
from .serializers import ProductImageSerializer, ProductImageUploadSerializer, ProductSerializer


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

    def post(self, request, pk=None):
        try:
            product = services.get_product(pk)
        except services.NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response({"detail": str(first_error)}, status=status.HTTP_400_BAD_REQUEST)
        image = serializer.save(product=product, uploaded_by=request.user)
        return Response(ProductImageSerializer(image).data, status=status.HTTP_201_CREATED)


class ProductImageDeleteView(APIView):
    def delete(self, request, pk=None, image_id=None):
        try:
            image = ProductImage.objects.get(pk=image_id, product_id=pk)
        except ProductImage.DoesNotExist:
            return Response({"detail": "Image not found."}, status=status.HTTP_404_NOT_FOUND)
        image.image.delete(save=False)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SuppliersView(APIView):
    def get(self, request):
        return Response(services.list_supplier_names())

    def post(self, request):
        try:
            names = services.create_supplier(request.data.get("name", ""))
        except services.ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(names, status=status.HTTP_201_CREATED)

    def delete(self, request):
        try:
            names = services.delete_supplier(request.data.get("name", ""))
        except services.ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(names)
