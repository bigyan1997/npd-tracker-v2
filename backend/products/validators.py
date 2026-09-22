from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB — generous for phone photos, small enough to keep disk sane


def validate_image_file_size(file):
    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image files must be 10MB or smaller.")
