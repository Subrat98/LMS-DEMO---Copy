from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.core.choices import PublishStatus
from apps.core.dates import today
from apps.ebooks.models import EBook
from apps.ebooks.validators import human_file_size


@transaction.atomic
def create_ebook(data: dict, actor=None) -> EBook:
    file = data.pop("file")
    is_published = data.pop("is_published", False)
    ebook = EBook.objects.create(
        **data,
        file=file,
        file_size_bytes=file.size,
        publish_status=PublishStatus.PUBLISHED if is_published else PublishStatus.DRAFT,
        uploaded_by=actor,
        uploaded_by_name=getattr(actor, "name", "") or getattr(actor, "username", ""),
        published_at=timezone.now() if is_published else None,
    )
    return ebook


@transaction.atomic
def update_ebook(ebook: EBook, data: dict, actor=None) -> EBook:
    file = data.pop("file", None)
    is_published = data.pop("is_published", None)
    for attr, value in data.items():
        setattr(ebook, attr, value)
    if file is not None:
        ebook.file = file
        ebook.file_size_bytes = file.size
    if is_published is not None:
        _apply_publish_status(ebook, is_published)
    ebook.save()
    return ebook


def _apply_publish_status(ebook: EBook, is_published: bool) -> None:
    if is_published and ebook.publish_status != PublishStatus.PUBLISHED:
        ebook.publish_status = PublishStatus.PUBLISHED
        ebook.published_at = timezone.now()
    elif not is_published:
        ebook.publish_status = PublishStatus.DRAFT
        ebook.published_at = None


@transaction.atomic
def toggle_publish_status(ebook: EBook, is_published: bool) -> EBook:
    _apply_publish_status(ebook, is_published)
    ebook.save(update_fields=["publish_status", "published_at"])
    return ebook


def delete_ebook(ebook: EBook) -> None:
    file_field = ebook.file
    ebook.delete()
    if file_field:
        file_field.delete(save=False)


def increment_download(ebook: EBook) -> None:
    EBook.objects.filter(pk=ebook.pk).update(download_count=F("download_count") + 1)


def display_file_size(ebook: EBook) -> str:
    return human_file_size(ebook.file_size_bytes)
