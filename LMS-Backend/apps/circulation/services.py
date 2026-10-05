from dataclasses import dataclass

from django.db import transaction

from apps.book_requests.models import BookRequest
from apps.catalogue import services as catalogue_services
from apps.catalogue.models import Book, BookCopy
from apps.circulation import calculators
from apps.circulation.models import Fine, Loan
from apps.core.choices import (
    CopyStatus,
    FineStatus,
    LoanStatus,
    OPEN_BOOKING_STATUSES,
    OPEN_REQUEST_STATUSES,
    RequestStatus,
)
from apps.core.dates import today
from apps.core.exceptions import BusinessRuleError
from apps.library_settings.services import get_settings
from apps.members.services import evaluate_block_status
from apps.reservations import services as reservation_services
from apps.reservations.models import Reservation


def assert_no_duplicate_title(member, book: Book, *, exclude_booking=None) -> None:
    """Rule 11: a member may not hold the same title via Booking + Loan + BookRequest
    simultaneously (Reservation is deliberately excluded, matching the frontend).
    """
    from apps.bookings.models import Booking  # local import: bookings depends on circulation

    bookings_qs = Booking.objects.filter(member=member, book=book, status__in=OPEN_BOOKING_STATUSES)
    if exclude_booking is not None:
        bookings_qs = bookings_qs.exclude(pk=exclude_booking.pk)
    if bookings_qs.exists():
        raise BusinessRuleError("DUPLICATE_TITLE", "You already have an open booking for this title.")

    if Loan.objects.filter(member=member, book=book, status=LoanStatus.ACTIVE).exists():
        raise BusinessRuleError("DUPLICATE_TITLE", "You already have this title on loan.")

    if BookRequest.objects.filter(member=member, book=book, status__in=OPEN_REQUEST_STATUSES).exists():
        raise BusinessRuleError("DUPLICATE_TITLE", "You already have an open request for this title.")


def _resolve_copy_for_issue(book: Book, copy_barcode: str | None, member, booking) -> BookCopy:
    if copy_barcode:
        barcode = copy_barcode.strip().upper()
        try:
            copy = BookCopy.objects.select_for_update().get(barcode=barcode, book=book)
        except BookCopy.DoesNotExist:
            raise BusinessRuleError("COPY_NOT_FOUND", "This copy does not belong to the given book.")

        if copy.status == CopyStatus.ISSUED:
            raise BusinessRuleError("COPY_ALREADY_ISSUED", "This copy is already issued.")
        if copy.status in (CopyStatus.LOST, CopyStatus.DAMAGED, CopyStatus.WITHDRAWN):
            raise BusinessRuleError("COPY_NOT_ISSUABLE", f"This copy is marked {copy.status} and cannot be issued.")
        if copy.status == CopyStatus.HELD:
            held_ref = catalogue_services.copy_held_for(copy)
            if held_ref is None:
                raise BusinessRuleError("COPY_HELD", "This copy is held and cannot be issued.")
            if held_ref.kind == "Booking":
                if booking is None or held_ref.ref != booking.booking_no:
                    raise BusinessRuleError(
                        "COPY_HELD_FOR_BOOKING", "This copy is held for a booking — use Verify Booking to issue it."
                    )
            elif held_ref.member_id != member.pk:
                raise BusinessRuleError("COPY_HELD_FOR_OTHER", "This copy is held for a different member.")
        return copy

    copy = catalogue_services.pick_available_copy(book)
    if copy is None:
        raise BusinessRuleError("NO_COPIES_AVAILABLE", "No copies of this title are currently available.")
    return copy


@transaction.atomic
def issue_book(*, member, book: Book, copy_barcode: str | None = None, booking=None, actor=None) -> Loan:
    from apps.core.choices import MemberStatus

    if member.status != MemberStatus.ACTIVE:
        raise BusinessRuleError("MEMBER_INACTIVE", "This member's account is not active.")

    settings = get_settings()
    block_status = evaluate_block_status(member, settings)
    if block_status.is_blocked and not block_status.is_overridden:
        raise BusinessRuleError(
            "MEMBER_BLOCKED", block_status.primary_reason or "This member is blocked from borrowing."
        )

    from apps.core.choices import BookStatus

    if book.status == BookStatus.RETIRED:
        raise BusinessRuleError("BOOK_RETIRED", "This title has been retired from the collection.")
    if book.library_use_only:
        raise BusinessRuleError("LIBRARY_USE_ONLY", "This title is for library use only and cannot be issued.")

    copy = _resolve_copy_for_issue(book, copy_barcode, member, booking)

    active_count = Loan.objects.filter(member=member, status=LoanStatus.ACTIVE).count()
    if not calculators.can_issue_more(active_count, settings):
        raise BusinessRuleError(
            "LOAN_LIMIT_REACHED", f"This member already has the maximum of {settings.max_concurrent_loans} book(s) issued."
        )

    issue_date = today()
    loan = Loan.objects.create(
        member=member,
        book=book,
        copy=copy,
        book_title=book.title,
        accession_number=book.accession_number,
        copy_barcode=copy.barcode,
        issue_date=issue_date,
        due_date=calculators.calculate_due_date(issue_date, settings),
        status=LoanStatus.ACTIVE,
        renewal_count=0,
        issued_by=actor,
    )
    catalogue_services.set_copy_status(copy, CopyStatus.ISSUED)

    matching_request = BookRequest.objects.filter(
        held_copy=copy, status=RequestStatus.APPROVED, member=member
    ).first()
    if matching_request:
        from apps.book_requests.services import mark_issued

        mark_issued(matching_request, loan)

    from apps.core.choices import ReservationStatus

    matching_reservation = Reservation.objects.filter(
        held_copy=copy, status=ReservationStatus.READY, member=member
    ).first()
    if matching_reservation:
        reservation_services.fulfil_for_loan(matching_reservation, loan)

    return loan


@dataclass
class ReturnResult:
    loan: Loan
    fine_amount: float
    fine: Fine | None
    promoted_reservation: Reservation | None


@transaction.atomic
def return_book(loan: Loan, actor=None) -> ReturnResult:
    if loan.status != LoanStatus.ACTIVE:
        raise BusinessRuleError("LOAN_ALREADY_RETURNED", "This loan has already been returned.")

    settings = get_settings()
    days, amount = calculators.calculate_fine(loan.due_date, settings)

    fine = None
    if amount > 0:
        fine = Fine.objects.filter(loan=loan, status=FineStatus.PENDING).first()
        if fine:
            fine.overdue_days = days
            fine.amount = amount
            fine.save(update_fields=["overdue_days", "amount"])
        else:
            fine = Fine.objects.create(
                loan=loan,
                member=loan.member,
                member_name=loan.member.name,
                book_title=loan.book_title,
                overdue_days=days,
                amount=amount,
                status=FineStatus.PENDING,
                created_date=today(),
            )

    loan.status = LoanStatus.RETURNED
    loan.return_date = today()
    loan.returned_by = actor
    loan.save(update_fields=["status", "return_date", "returned_by"])

    if hasattr(loan, "booking"):
        from apps.bookings.services import mark_returned_by_loan  # local import: breaks the one cycle

        mark_returned_by_loan(loan.booking, actor)

    promoted = reservation_services.promote_next(loan.book, loan.copy)
    if promoted is None:
        catalogue_services.release_copy(loan.copy)

    return ReturnResult(loan=loan, fine_amount=amount, fine=fine, promoted_reservation=promoted)


@transaction.atomic
def return_by_barcode(barcode: str, actor=None) -> ReturnResult:
    try:
        loan = Loan.objects.select_for_update().get(
            copy__barcode=barcode.strip().upper(), status=LoanStatus.ACTIVE
        )
    except Loan.DoesNotExist:
        raise BusinessRuleError("ACTIVE_LOAN_NOT_FOUND", "No active loan was found for this copy.")
    return return_book(loan, actor=actor)


@transaction.atomic
def renew_loan(loan: Loan, actor=None) -> Loan:
    settings = get_settings()
    has_pending = reservation_services.has_pending_reservation(loan.book)
    allowed, reason = calculators.can_renew(loan, has_pending, settings)
    if not allowed:
        raise BusinessRuleError("RENEWAL_BLOCKED", reason)

    loan.due_date = calculators.calculate_renewed_due_date(loan, settings)
    loan.renewal_count += 1
    loan.save(update_fields=["due_date", "renewal_count"])
    return loan


@transaction.atomic
def collect_fine(fine: Fine, actor=None) -> Fine:
    if fine.status != FineStatus.PENDING:
        raise BusinessRuleError("FINE_NOT_PENDING", "Only a pending fine can be collected.")
    fine.status = FineStatus.COLLECTED
    fine.collected_date = today()
    fine.actioned_by = actor
    fine.save(update_fields=["status", "collected_date", "actioned_by"])
    return fine


@transaction.atomic
def waive_fine(fine: Fine, reason: str, actor=None) -> Fine:
    if fine.status != FineStatus.PENDING:
        raise BusinessRuleError("FINE_NOT_PENDING", "Only a pending fine can be waived.")
    fine.status = FineStatus.WAIVED
    fine.reason = reason
    fine.collected_date = today()
    fine.actioned_by = actor
    fine.save(update_fields=["status", "reason", "collected_date", "actioned_by"])
    return fine
