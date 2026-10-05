import os

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = (".pdf", ".epub")


def validate_ebook_file(file) -> None:
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}.")
    max_bytes = getattr(settings, "EBOOK_MAX_UPLOAD_MB", 50) * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f"File is too large (max {settings.EBOOK_MAX_UPLOAD_MB} MB).")


def human_file_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
