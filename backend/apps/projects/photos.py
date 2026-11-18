"""Photo upload checks and access rules."""

from django.conf import settings
from ninja.errors import HttpError

from apps.accounts.permissions import is_office

# Recognize real images by their first bytes, not by the file name or browser-sent type.
_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)
_HEIC_BRANDS = (b"heic", b"heix", b"hevc", b"heif", b"mif1", b"msf1")


def detect_image_type(head: bytes) -> str | None:
    for signature, content_type in _SIGNATURES:
        if head.startswith(signature):
            return content_type
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp" and head[8:12] in _HEIC_BRANDS:
        return "image/heic"
    return None


def validate_upload(uploaded_file) -> str:
    """Return the detected content type, or raise 422."""
    if uploaded_file.size > settings.PHOTO_MAX_BYTES:
        limit_mb = settings.PHOTO_MAX_BYTES // (1024 * 1024)
        raise HttpError(422, f"{uploaded_file.name} is larger than {limit_mb} MB.")
    head = uploaded_file.read(16)
    uploaded_file.seek(0)
    content_type = detect_image_type(head)
    if content_type is None:
        raise HttpError(422, f"{uploaded_file.name} is not a JPEG, PNG, WebP or HEIC image.")
    return content_type


def can_view_project_files(user, project) -> bool:
    """Office staff see every photo; crew members only photos of jobs assigned to them."""
    if is_office(user):
        return True
    from apps.workorders.models import WorkOrderAssignment

    return WorkOrderAssignment.objects.filter(user=user, work_order__project=project).exists()
