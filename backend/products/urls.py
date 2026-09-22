from django.urls import path
from rest_framework.routers import DefaultRouter

from .schema_view import SchemaView
from .views import (
    DeletedProductsView,
    ProductImageDeleteView,
    ProductImageUploadView,
    ProductViewSet,
    RestoreProductView,
    SuppliersView,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")

urlpatterns = [
    path("schema/", SchemaView.as_view(), name="schema"),
    path("suppliers/", SuppliersView.as_view(), name="suppliers"),
    # Must come before the router's products/<pk>/ pattern, which would
    # otherwise swallow "deleted" as if it were a product id.
    path("products/deleted/", DeletedProductsView.as_view(), name="deleted-products"),
    path("products/deleted/<int:pk>/restore/", RestoreProductView.as_view(), name="restore-product"),
    path("products/<int:pk>/images/", ProductImageUploadView.as_view(), name="product-image-upload"),
    path(
        "products/<int:pk>/images/<int:image_id>/",
        ProductImageDeleteView.as_view(),
        name="product-image-delete",
    ),
    *router.urls,
]
