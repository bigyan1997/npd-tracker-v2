"""
Serves product photo bytes to the browser, whether the photo is in Google
Drive or (dev/tests, Drive not configured) on local disk. Going through the
app rather than linking straight to Drive means staff who only use the
tracker see every photo without needing Drive access, and the whole thing
works with DEBUG off (Django doesn't serve MEDIA_ROOT then).

Gallery thumbnails are small JPEGs cached on local disk — re-downloading a
5MB phone photo from Drive for every 80px tile would be slow over Tailscale.
Full-size photos are fetched from Drive on demand and not cached (that
would just mirror Drive onto this PC's disk).
"""

import io
import mimetypes

from django.conf import settings
from PIL import Image, ImageOps

from .drive_client import DriveClient

THUMB_SIZE = 400
# Formats every browser shows natively. Anything else (iPhone HEIC, TIFF…)
# or anything that could carry script (SVG) is shown via Drive's rendered
# preview instead of served raw.
BROWSER_SAFE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/avif", "image/bmp", "application/pdf"}
PDF = "application/pdf"


def _cache_dir():
    path = settings.MEDIA_ROOT / "photo_thumbs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def version(image):
    stamp = image.drive_modified_at or image.uploaded_at
    return int(stamp.timestamp()) if stamp else 0


def _thumb_cache_path(image):
    key = image.drive_file_id or f"local{image.pk}"
    return _cache_dir() / f"{key}_{version(image)}.jpg"


def clear_cached(image):
    key = image.drive_file_id or f"local{image.pk}"
    for path in _cache_dir().glob(f"{key}_*.jpg"):
        path.unlink(missing_ok=True)


def _to_jpeg(content, size=None):
    img = Image.open(io.BytesIO(content))
    img = ImageOps.exif_transpose(img)  # phone photos store rotation in EXIF
    if size:
        img.thumbnail((size, size))
    if img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, "JPEG", quality=82)
    return out.getvalue()


def _mime(image):
    return image.mime_type or mimetypes.guess_type(image.image.name or "")[0] or ""


def _drive_preview(client, image, size):
    # Stored thumbnail links expire after a few hours — always ask for a fresh one.
    link = client.get_meta(image.drive_file_id).get("thumbnailLink")
    content, _ = client.download_thumbnail(link, size)
    return _to_jpeg(content)


def thumbnail(image):
    """(bytes, content_type) for the gallery tile."""
    path = _thumb_cache_path(image)
    if path.exists():
        return path.read_bytes(), "image/jpeg"
    if image.drive_file_id and _mime(image) == PDF:
        data = _drive_preview(DriveClient(), image, THUMB_SIZE)  # Drive renders page 1
    elif image.drive_file_id:
        client = DriveClient()
        try:
            data = _to_jpeg(client.download(image.drive_file_id), THUMB_SIZE)
        except (OSError, Image.DecompressionBombError):
            data = _drive_preview(client, image, THUMB_SIZE)  # Pillow can't read it (e.g. HEIC)
    else:
        with image.image.open("rb") as f:
            data = _to_jpeg(f.read(), THUMB_SIZE)
    clear_cached(image)  # drop older versions of this photo
    path.write_bytes(data)
    return data, "image/jpeg"


def full(image):
    """(bytes, content_type) for viewing the photo at full size."""
    mime = _mime(image)
    if not image.drive_file_id:
        with image.image.open("rb") as f:
            return f.read(), mime or "application/octet-stream"
    client = DriveClient()
    if mime in BROWSER_SAFE_TYPES:
        return client.download(image.drive_file_id), mime
    return _drive_preview(client, image, 2000), "image/jpeg"

