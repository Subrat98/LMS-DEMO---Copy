import csv
import io
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Max, Q

from apps.core.choices import BookStatus, Classification, CopyStatus
from apps.core.dates import today
from apps.core.exceptions import BusinessRuleError
from apps.catalogue.models import Book, BookCopy


# ---------------------------------------------------------------------------
# The available-copies invariant. Nothing else may write total_copies/available_copies
# or Book.status — every path below funnels through _sync_book_counts().
# ---------------------------------------------------------------------------


def _sync_book_counts(book: Book) -> Book:
    counts = book.copies.aggregate(
        total=Count("id"),
        available=Count("id", filter=Q(status=CopyStatus.AVAILABLE)),
    )
    book.total_copies = counts["total"] or 0
    book.available_copies = counts["available"] or 0
    if book.status != BookStatus.RETIRED:
        book.status = BookStatus.AVAILABLE if book.available_copies > 0 else BookStatus.FULLY_ISSUED
    book.save(update_fields=["total_copies", "available_copies", "status", "stream", "syllabus_streams"])
    return book


def _lock_book(book: Book) -> Book:
    return Book.objects.select_for_update().get(pk=book.pk)


@transaction.atomic
def set_copy_status(copy: BookCopy, new_status: str, *, reason: str = "", actor=None) -> BookCopy:
    book = _lock_book(copy.book)
    copy.status = new_status
    copy.status_reason = reason
    copy.status_changed_date = today()
    copy.save(update_fields=["status", "status_reason", "status_changed_date"])
    _sync_book_counts(book)
    copy.refresh_from_db()
    return copy


def pick_available_copy(book: Book) -> BookCopy | None:
    return (
        book.copies.select_for_update()
        .filter(status=CopyStatus.AVAILABLE)
        .order_by("copy_number")
        .first()
    )


@transaction.atomic
def hold_copy(book: Book) -> BookCopy:
    copy = pick_available_copy(book)
    if copy is None:
        raise BusinessRuleError("NO_COPIES_AVAILABLE", "No copies of this title are currently available.")
    return set_copy_status(copy, CopyStatus.HELD)


@transaction.atomic
def release_copy(copy: BookCopy) -> BookCopy:
    return set_copy_status(copy, CopyStatus.AVAILABLE)


def next_copy_number(book: Book) -> int:
    current_max = book.copies.aggregate(m=Max("copy_number"))["m"] or 0
    return current_max + 1


@transaction.atomic
def add_copies(book: Book, count: int, actor=None) -> list[BookCopy]:
    book = _lock_book(book)
    start = next_copy_number(book)
    new_copies = [
        BookCopy(
            book=book,
            copy_number=start + i,
            barcode=f"{book.accession_number}-{(start + i):02d}",
            status=CopyStatus.AVAILABLE,
        )
        for i in range(count)
    ]
    BookCopy.objects.bulk_create(new_copies)
    _sync_book_counts(book)
    return list(book.copies.filter(copy_number__gte=start))


@transaction.atomic
def remove_available_copies(book: Book, count: int) -> int:
    book = _lock_book(book)
    removable = list(
        book.copies.filter(status=CopyStatus.AVAILABLE).order_by("-copy_number")[:count]
    )
    if len(removable) < count:
        raise BusinessRuleError(
            "INSUFFICIENT_AVAILABLE_COPIES",
            f"Only {len(removable)} available copies can be removed; {count} were requested.",
        )
    BookCopy.objects.filter(pk__in=[c.pk for c in removable]).delete()
    _sync_book_counts(book)
    return len(removable)


@transaction.atomic
def create_book(data: dict, actor=None) -> Book:
    total_copies = data.pop("total_copies")
    book = Book.objects.create(**data, total_copies=0, available_copies=0)
    add_copies(book, total_copies, actor=actor)
    book.refresh_from_db()
    return book


@transaction.atomic
def update_book(book: Book, data: dict, actor=None) -> Book:
    new_total = data.pop("total_copies", None)
    for attr, value in data.items():
        setattr(book, attr, value)
    book.save()

    if new_total is not None and new_total != book.total_copies:
        delta = new_total - book.total_copies
        if delta > 0:
            add_copies(book, delta, actor=actor)
        else:
            remove_available_copies(book, -delta)
    book.refresh_from_db()
    return book


@transaction.atomic
def retire_book(book: Book, actor=None) -> Book:
    book.status = BookStatus.RETIRED
    book.save(update_fields=["status"])
    return book


@transaction.atomic
def reinstate_book(book: Book, actor=None) -> Book:
    book.status = BookStatus.AVAILABLE if book.available_copies > 0 else BookStatus.FULLY_ISSUED
    book.save(update_fields=["status"])
    return book


def delete_book(book: Book) -> None:
    from django.db.models import ProtectedError

    try:
        book.delete()
    except ProtectedError as exc:
        raise BusinessRuleError(
            "BOOK_HAS_HISTORY",
            "This book has loan or booking history and cannot be deleted. Retire it instead.",
        ) from exc


@dataclass
class HoldRef:
    kind: str  # 'Booking' | 'Request' | 'Reservation'
    ref: str
    member_id: int


def copy_held_for(copy: BookCopy) -> HoldRef | None:
    """Looks for an open Booking, an Approved BookRequest, or a Ready Reservation holding this copy."""
    from apps.bookings.models import Booking
    from apps.book_requests.models import BookRequest
    from apps.core.choices import OPEN_BOOKING_STATUSES, RequestStatus, ReservationStatus
    from apps.reservations.models import Reservation

    booking = Booking.objects.filter(held_copy=copy, status__in=OPEN_BOOKING_STATUSES).first()
    if booking:
        return HoldRef("Booking", booking.booking_no, booking.member_id)

    req = BookRequest.objects.filter(held_copy=copy, status=RequestStatus.APPROVED).first()
    if req:
        return HoldRef("Request", str(req.pk), req.member_id)

    res = Reservation.objects.filter(held_copy=copy, status=ReservationStatus.READY).first()
    if res:
        return HoldRef("Reservation", str(res.pk), res.member_id)

    return None


def change_copy_status_manual(copy: BookCopy, new_status: str, reason: str, actor=None) -> BookCopy:
    from apps.core.choices import REASON_REQUIRED_COPY_STATUSES

    if copy.status in (CopyStatus.ISSUED, CopyStatus.HELD):
        raise BusinessRuleError(
            "COPY_IN_CIRCULATION", "This copy is issued or held and cannot have its status changed directly."
        )
    if new_status in REASON_REQUIRED_COPY_STATUSES and not reason.strip():
        raise BusinessRuleError("REASON_REQUIRED", f"A reason is required to mark a copy as {new_status}.")
    return set_copy_status(copy, new_status, reason=reason, actor=actor)


# ---------------------------------------------------------------------------
# Bulk CSV import (FR-CAT-03) — ported from BulkImportModal.tsx.
# Columns (positional): AccessionNumber, Title, Author, Subject, Classification,
# Publisher, Edition, ISBN, Price, Copies, ShelfLocation, LibraryUseOnly
# ---------------------------------------------------------------------------

_CLASSIFICATION_KEYWORDS = (
    ("art", Classification.STREAM_ARTS),
    ("science", Classification.STREAM_SCIENCE),
    ("journal", Classification.JOURNALS),
    ("affair", Classification.CURRENT_AFFAIRS),
)


def _match_classification(raw: str) -> str:
    raw = (raw or "").strip()
    for choice in Classification.values:
        if raw.lower() == choice.lower():
            return choice
    lowered = raw.lower()
    for keyword, choice in _CLASSIFICATION_KEYWORDS:
        if keyword in lowered:
            return choice.value
    return Classification.COURSE


@transaction.atomic
def bulk_import_books(file, actor=None) -> dict:
    text = file.read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if rows and rows[0] and rows[0][0].strip().lower().startswith("accession"):
        rows = rows[1:]

    existing_accessions = {a.lower() for a in Book.objects.values_list("accession_number", flat=True)}
    batch_accessions: set[str] = set()
    imported = 0
    errors = []

    for row_number, row in enumerate(rows, start=1):
        try:
            with transaction.atomic():
                row = row + [""] * (12 - len(row))
                (
                    accession,
                    title,
                    author,
                    subject,
                    classification_raw,
                    publisher,
                    edition,
                    isbn,
                    price_raw,
                    copies_raw,
                    shelf_location,
                    library_use_only_raw,
                ) = row[:12]

                accession = accession.strip()
                if not accession:
                    raise BusinessRuleError("ROW_INVALID", "Accession number is required.")
                if accession.lower() in existing_accessions or accession.lower() in batch_accessions:
                    raise BusinessRuleError("ROW_INVALID", f"Duplicate accession number '{accession}'.")
                if not title.strip():
                    raise BusinessRuleError("ROW_INVALID", "Title is required.")
                if not author.strip():
                    raise BusinessRuleError("ROW_INVALID", "Author is required.")
                if not subject.strip():
                    raise BusinessRuleError("ROW_INVALID", "Subject is required.")

                try:
                    copies_num = int(str(copies_raw).strip())
                except ValueError:
                    copies_num = -1
                if copies_num < 1:
                    raise BusinessRuleError("ROW_INVALID", "Copies must be an integer of at least 1.")

                if not shelf_location.strip():
                    raise BusinessRuleError("ROW_INVALID", "Shelf location is required.")

                try:
                    price = float(price_raw)
                except (TypeError, ValueError):
                    price = 0

                library_use_only = library_use_only_raw.strip().lower() in ("true", "1")
                classification = _match_classification(classification_raw)

                create_book(
                    {
                        "accession_number": accession,
                        "title": title.strip(),
                        "author": author.strip(),
                        "subject": subject.strip(),
                        "category": "Reference",
                        "classification": classification,
                        "publisher": publisher.strip() or "",
                        "edition": edition.strip() or "",
                        "isbn": isbn.strip() or "",
                        "price": price,
                        "shelf_location": shelf_location.strip(),
                        "library_use_only": library_use_only,
                        "total_copies": copies_num,
                    },
                    actor=actor,
                )
                batch_accessions.add(accession.lower())
                imported += 1
        except BusinessRuleError as exc:
            errors.append({"rowNumber": row_number, "data": row, "reason": exc.message})

    return {"imported": imported, "failed": len(errors), "errors": errors}
