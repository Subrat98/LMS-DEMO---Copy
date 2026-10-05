from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking, BookingAuditEntry, BookingSequence
from apps.catalogue import services as catalogue_services
from apps.catalogue.models import Book
from apps.circulation.services import assert_no_duplicate_title, issue_book
from apps.core.choices import AuditAction, BookStatus, OPEN_BOOKING_STATUSES, Role
from apps.core.dates import add_days, today
from apps.core.exceptions import BusinessRuleError
from apps.core.stream import is_visible_to_member
from apps.library_settings.services import get_settings

SYSTEM_ACTOR_NAME = "System"


def normalize_booking_no(value: str) -> str:
    return value.strip().upper()


@transaction.atomic
def next_booking_no(year: int) -> str:
    seq_row, _ = BookingSequence.objects.select_for_update().get_or_create(year=year)
    seq_row.last_seq += 1
    seq_row.save(update_fields=["last_seq"])
    return f"BK-{year}-{seq_row.last_seq:06d}"


def _audit(actor, action: str, booking_no: str, *, reason: str = "", details: str = "") -> None:
    if actor is None:
        user, user_name, role = None, SYSTEM_ACTOR_NAME, "system"
    else:
        user, user_name, role = actor, actor.name or actor.username, actor.role
    BookingAuditEntry.objects.create(
        booking_no=booking_no,
        user=user,
        user_name=user_name,
        role=role,
        action=action,
        cancellation_reason=reason,
        details=details,
    )


def _assert_bookable(member, book: Book, *, exclude_booking=None) -> None:
    if book.status == BookStatus.RETIRED:
        raise BusinessRuleError("BOOK_RETIRED", "This title has been retired from the collection.")
    if book.library_use_only:
        raise BusinessRuleError("LIBRARY_USE_ONLY", "This title is for library use only and cannot be booked.")
    if book.available_copies <= 0:
        raise BusinessRuleError("NO_COPIES_AVAILABLE", "No copies of this title are currently available.")

    assert_no_duplicate_title(member, book, exclude_booking=exclude_booking)

    if not is_visible_to_member(book, member):
        raise BusinessRuleError("OUT_OF_STREAM", "This title is outside your programme's stream.")

    from apps.circulation.models import Loan
    from apps.core.choices import LoanStatus

    settings = get_settings()
    active_loans = Loan.objects.filter(member=member, status=LoanStatus.ACTIVE).count()
    open_bookings = Booking.objects.filter(member=member, status__in=OPEN_BOOKING_STATUSES)
    if exclude_booking is not None:
        open_bookings = open_bookings.exclude(pk=exclude_booking.pk)
    if active_loans + open_bookings.count() >= settings.max_concurrent_loans:
        raise BusinessRuleError(
            "BOOKING_LIMIT_REACHED", f"You already have the maximum of {settings.max_concurrent_loans} book(s) issued/booked."
        )


@transaction.atomic
def create_booking(member, book: Book, actor=None) -> Booking:
    _assert_bookable(member, book)
    copy = catalogue_services.hold_copy(book)
    settings = get_settings()
    booking = Booking.objects.create(
        booking_no=next_booking_no(today().year),
        member=member,
        student_name=member.name,
        book=book,
        accession_number=book.accession_number,
        book_title=book.title,
        expiry_date=add_days(today(), settings.reservation_hold_days),
        status="Booked",
        held_copy=copy,
    )
    _audit(actor, AuditAction.CREATE, booking.booking_no)
    return booking


@transaction.atomic
def update_booking(booking: Booking, new_book: Book, actor) -> Booking:
    if booking.status != "Booked":
        raise BusinessRuleError("BOOKING_NOT_EDITABLE", "Only a booking that hasn't been verified yet can be changed.")
    if actor is not None and actor.role == Role.STUDENT and actor.member_id != booking.member_id:
        raise BusinessRuleError("NOT_YOUR_BOOKING", "You can only change your own booking.")

    _assert_bookable(booking.member, new_book, exclude_booking=booking)
    old_copy = booking.held_copy
    old_title = booking.book_title
    new_copy = catalogue_services.hold_copy(new_book)

    settings = get_settings()
    booking.book = new_book
    booking.accession_number = new_book.accession_number
    booking.book_title = new_book.title
    booking.held_copy = new_copy
    booking.expiry_date = add_days(today(), settings.reservation_hold_days)
    booking.save(update_fields=["book", "accession_number", "book_title", "held_copy", "expiry_date", "updated_at"])

    if old_copy is not None:
        catalogue_services.release_copy(old_copy)

    _audit(actor, AuditAction.UPDATE, booking.booking_no, details=f'Changed "{old_title}" -> "{new_book.title}"')
    return booking


@transaction.atomic
def cancel_booking(booking: Booking, actor, reason: str = "", *, system: bool = False) -> Booking:
    if system:
        pass
    elif actor is not None and actor.role == Role.STUDENT:
        if actor.member_id != booking.member_id or booking.status != "Booked":
            raise BusinessRuleError(
                "CANNOT_CANCEL", "You can only cancel your own booking, and only before it's verified."
            )
    else:
        if booking.status not in OPEN_BOOKING_STATUSES:
            raise BusinessRuleError("BOOKING_NOT_OPEN", "Only a Booked or Verified booking can be cancelled.")
        if not reason.strip():
            raise BusinessRuleError("REASON_REQUIRED", "A cancellation reason is required.")

    held_copy = booking.held_copy
    booking.status = "Cancelled"
    booking.cancelled_by = actor
    booking.cancelled_by_name = SYSTEM_ACTOR_NAME if actor is None else (actor.name or actor.username)
    booking.cancelled_at = timezone.now()
    booking.cancellation_reason = reason
    booking.save(
        update_fields=["status", "cancelled_by", "cancelled_by_name", "cancelled_at", "cancellation_reason", "updated_at"]
    )
    if held_copy is not None:
        catalogue_services.release_copy(held_copy)

    _audit(actor, AuditAction.CANCEL, booking.booking_no, reason=reason)
    return booking


def lookup_booking(booking_no: str, roll_number: str | None = None) -> Booking:
    booking_no = normalize_booking_no(booking_no)
    try:
        booking = Booking.objects.select_related("member", "book", "held_copy").get(booking_no=booking_no)
    except Booking.DoesNotExist:
        raise BusinessRuleError("BOOKING_NOT_FOUND", f"No booking found with number '{booking_no}'.")

    if roll_number and booking.member.roll_number.lower() != roll_number.strip().lower():
        raise BusinessRuleError("BOOKING_STUDENT_MISMATCH", "This booking does not belong to the given student.")

    if booking.status in OPEN_BOOKING_STATUSES and booking.expiry_date < today():
        cancel_booking(
            booking, None, "Booking expired — not collected within hold period", system=True
        )
        raise BusinessRuleError("BOOKING_EXPIRED", "This booking has expired and was not collected in time.")

    if booking.status == "Cancelled":
        raise BusinessRuleError("BOOKING_CANCELLED", "This booking has been cancelled.")
    if booking.status == "Issued":
        raise BusinessRuleError("BOOKING_ALREADY_ISSUED", "This booking has already been issued.")
    if booking.status == "Returned":
        raise BusinessRuleError("BOOKING_ALREADY_RETURNED", "This booking's book has already been returned.")

    return booking


@transaction.atomic
def verify_booking(booking_no: str, roll_number: str | None, actor) -> Booking:
    booking = lookup_booking(booking_no, roll_number)
    if booking.status == "Verified":
        return booking
    booking.status = "Verified"
    booking.verified_by = actor
    booking.verified_by_name = actor.name or actor.username if actor else SYSTEM_ACTOR_NAME
    booking.verified_at = timezone.now()
    booking.save(update_fields=["status", "verified_by", "verified_by_name", "verified_at", "updated_at"])
    _audit(actor, AuditAction.VERIFY, booking.booking_no)
    return booking


@transaction.atomic
def issue_booking(booking_no: str, roll_number: str | None, actor) -> tuple[Booking, "object"]:
    booking = lookup_booking(booking_no, roll_number)
    if booking.status == "Booked":
        booking = verify_booking(booking.booking_no, roll_number, actor)

    loan = issue_book(
        member=booking.member,
        book=booking.book,
        copy_barcode=booking.held_copy.barcode,
        booking=booking,
        actor=actor,
    )
    booking.loan = loan
    booking.status = "Issued"
    booking.issued_by = actor
    booking.issued_by_name = actor.name or actor.username if actor else SYSTEM_ACTOR_NAME
    booking.issued_at = timezone.now()
    booking.save(update_fields=["loan", "status", "issued_by", "issued_by_name", "issued_at", "updated_at"])
    _audit(actor, AuditAction.ISSUE, booking.booking_no, details=f"Issued copy {loan.copy_barcode}, due {loan.due_date}")
    return booking, loan


@transaction.atomic
def mark_returned_by_loan(booking: Booking, actor=None) -> Booking:
    booking.status = "Returned"
    booking.returned_at = timezone.now()
    booking.save(update_fields=["status", "returned_at", "updated_at"])
    _audit(actor, AuditAction.RETURN, booking.booking_no)
    return booking


@transaction.atomic
def expire_open_bookings(ref_date=None) -> int:
    ref_date = ref_date or today()
    expiring = list(Booking.objects.filter(status__in=OPEN_BOOKING_STATUSES, expiry_date__lt=ref_date))
    for booking in expiring:
        cancel_booking(booking, None, "Booking expired — not collected within hold period", system=True)
    return len(expiring)
