from django.db import transaction

from apps.book_requests.models import BookRequest
from apps.catalogue import services as catalogue_services
from apps.catalogue.models import Book
from apps.core.choices import RequestStatus
from apps.core.dates import add_days, today
from apps.core.exceptions import BusinessRuleError
from apps.library_settings.services import get_settings


@transaction.atomic
def create_request(member, book: Book, actor=None) -> BookRequest:
    from apps.circulation.services import assert_no_duplicate_title

    if book.library_use_only:
        raise BusinessRuleError("LIBRARY_USE_ONLY", "This title is for library use only and cannot be borrowed.")
    if book.available_copies <= 0:
        raise BusinessRuleError("NO_COPIES_AVAILABLE", "No copies of this title are currently available.")

    from apps.circulation.models import Loan
    from apps.core.choices import LoanStatus

    settings = get_settings()
    active_loans = Loan.objects.filter(member=member, status=LoanStatus.ACTIVE).count()
    if active_loans >= settings.max_concurrent_loans:
        raise BusinessRuleError("LOAN_LIMIT_REACHED", "You already have the maximum number of books issued.")

    assert_no_duplicate_title(member, book)

    return BookRequest.objects.create(
        member=member,
        book=book,
        accession_number=book.accession_number,
        book_title=book.title,
        status=RequestStatus.PENDING,
    )


@transaction.atomic
def approve_request(req: BookRequest, actor=None) -> BookRequest:
    if req.status != RequestStatus.PENDING:
        raise BusinessRuleError("REQUEST_NOT_PENDING", "Only a pending request can be approved.")
    copy = catalogue_services.hold_copy(req.book)
    settings = get_settings()
    req.status = RequestStatus.APPROVED
    req.held_copy = copy
    req.ready_date = today()
    req.expiry_date = add_days(today(), settings.reservation_hold_days)
    req.actioned_by = actor
    req.save(update_fields=["status", "held_copy", "ready_date", "expiry_date", "actioned_by"])
    return req


@transaction.atomic
def reject_request(req: BookRequest, reason: str = "", actor=None) -> BookRequest:
    if req.status != RequestStatus.PENDING:
        raise BusinessRuleError("REQUEST_NOT_PENDING", "Only a pending request can be rejected.")
    req.status = RequestStatus.REJECTED
    req.reject_reason = reason
    req.actioned_by = actor
    req.save(update_fields=["status", "reject_reason", "actioned_by"])
    return req


@transaction.atomic
def cancel_request(req: BookRequest, actor=None) -> BookRequest:
    if req.status == RequestStatus.ISSUED:
        return req
    if req.status == RequestStatus.APPROVED and req.held_copy is not None:
        catalogue_services.release_copy(req.held_copy)
    req.status = RequestStatus.CANCELLED
    req.save(update_fields=["status"])
    return req


@transaction.atomic
def mark_issued(req: BookRequest, loan) -> BookRequest:
    req.status = RequestStatus.ISSUED
    req.loan = loan
    req.save(update_fields=["status", "loan"])
    return req


def has_open_request(member, book: Book) -> bool:
    from apps.core.choices import OPEN_REQUEST_STATUSES

    return BookRequest.objects.filter(member=member, book=book, status__in=OPEN_REQUEST_STATUSES).exists()


@transaction.atomic
def expire_approved_requests(ref_date=None) -> int:
    ref_date = ref_date or today()
    expiring = list(
        BookRequest.objects.select_related("held_copy").filter(
            status=RequestStatus.APPROVED, expiry_date__lt=ref_date
        )
    )
    for req in expiring:
        if req.held_copy is not None:
            catalogue_services.release_copy(req.held_copy)
        req.status = RequestStatus.EXPIRED
        req.save(update_fields=["status"])
    return len(expiring)
