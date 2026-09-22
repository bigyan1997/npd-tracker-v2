from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, HttpResponseNotFound
from django.urls import include, path, re_path


def serve_frontend_index(request, *args, **kwargs):
    index_path = settings.FRONTEND_DIST / "index.html"
    if not index_path.exists():
        return HttpResponseNotFound("Frontend build not found. Run `npm run build` in frontend/.")
    return FileResponse(open(index_path, "rb"))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("products.urls")),
    re_path(r"^(?!api(/|$)|admin(/|$)|static(/|$)|media(/|$)).*$", serve_frontend_index),
]

if settings.DEBUG:
    urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + urlpatterns
