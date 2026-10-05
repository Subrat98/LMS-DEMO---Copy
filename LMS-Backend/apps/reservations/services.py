from django.db import transaction

from apps.catalogue import services as catalogue_services
from apps.catalogue.models import Book, BookCopy
from apps.core.choices import PENDING_RESERVATION_STATUSES, ReservationStatus
from apps.core.dates import add_days, today
from apps.library_settings.services import get_settings
from apps.reservations.models import Reservation


@transaction.atomic
def reserve(member, book: Book, actor=None) -> Reservation:
    """No validation at all, matching the frontend — simplest of the three 'hold' flows."""
    position = (
        Reservation.objects.filter(book=book, status__in=PENDING_RESERVATION_STATUSES).count() + 1
    )
    return Reservation.objects.create(
        member=member,
        book=book,
        accession_number=book.accession_number,
        book_title=book.title,
        queue_position=position,
        status=ReservationStatus.WAITING,
    )


def has_pending_reservation(book: Book, exclude_member=None) -> bool:
    qs = Reservation.objects.filter(book=book, status__in=PENDING_RESERVATION_STATUSES)
    if exclude_member is not None:
        qs = qs.exclude(member=exclude_member)
    return qs.exists()


@transaction.atomic
def promote_next(book: Book, freed_copy: BookCopy) -> Reservation | None:
    next_res = (
        Reservation.objects.filter(book=book, status=ReservationStatus.WAITING)
        .order_by("queue_position")
        .first()
    )
    if next_res is None:
        return None
    settings = get_settings()
    next_res.status = ReservationStatus.READY
    next_res.ready_date = today()
    next_res.expiry_date = add_days(today(), settings.reservation_hold_days)
    next_res.held_copy = freed_copy
    next_res.save(update_fields=["status", "ready_date", "expiry_date", "held_copy"])
    catalogue_services.set_copy_status(freed_copy, "Held")
    return next_res


@transaction.atomic
def _hand_off(copy: BookCopy) -> None:
    book = copy.book
    promoted = promote_next(book, copy)
    if promoted is None:
        catalogue_services.release_copy(copy)


@transaction.atomic
def cancel_reservation(reservation: Reservation, actor=None) -> Reservation:
    was_ready = reservation.status == ReservationStatus.READY
    held_copy = reservation.held_copy
    reservation.status = ReservationStatus.CANCELLED
    reservation.save(update_fields=["status"])
    if was_ready and held_copy is not None:
        _hand_off(held_copy)
    return reservation


@transaction.atomic
def fulfil_for_loan(reservation: Reservation, loan) -> Reservation:
    reservation.status = ReservationStatus.FULFILLED
    reservation.loan = loan
    reservation.save(update_fields=["status", "loan"])
    return reservation


@transaction.atomic
def expire_ready_reservations(ref_date=None) -> int:
    ref_date = ref_date or today()
    expiring = list(
        Reservation.objects.select_related("held_copy").filter(
            status=ReservationStatus.READY, expiry_date__lt=ref_date
        )
    )
    for reservation in expiring:
        held_copy = reservation.held_copy
        reservation.status = ReservationStatus.EXPIRED
        reservation.save(update_fields=["status"])
        if held_copy is not None:
            _hand_off(held_copy)
    return len(expiring)
