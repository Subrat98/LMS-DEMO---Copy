import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.dates import today

logger = logging.getLogger("lms.jobs")


class Command(BaseCommand):
    help = "Expires overdue-to-collect bookings, approved book requests, and ready reservations."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Run as of this date (YYYY-MM-DD) instead of today.")
        parser.add_argument("--dry-run", action="store_true", help="Report counts without making changes.")

    def handle(self, *args, **options):
        from datetime import datetime

        ref_date = datetime.strptime(options["date"], "%Y-%m-%d").date() if options.get("date") else today()
        dry_run = options["dry_run"]

        if dry_run:
            self._report_dry_run(ref_date)
            return

        from apps.book_requests.services import expire_approved_requests
        from apps.bookings.services import expire_open_bookings
        from apps.reservations.services import expire_ready_reservations

        with transaction.atomic():
            bookings_expired = expire_open_bookings(ref_date)
        with transaction.atomic():
            requests_expired = expire_approved_requests(ref_date)
        with transaction.atomic():
            reservations_expired = expire_ready_reservations(ref_date)

        message = (
            f"Expired {bookings_expired} booking(s), {requests_expired} book request(s), "
            f"{reservations_expired} reservation(s) as of {ref_date}."
        )
        logger.info(message)
        self.stdout.write(self.style.SUCCESS(message))

    def _report_dry_run(self, ref_date):
        from apps.book_requests.models import BookRequest
        from apps.bookings.models import Booking
        from apps.core.choices import OPEN_BOOKING_STATUSES, RequestStatus, ReservationStatus
        from apps.reservations.models import Reservation

        bookings = Booking.objects.filter(status__in=OPEN_BOOKING_STATUSES, expiry_date__lt=ref_date).count()
        requests = BookRequest.objects.filter(status=RequestStatus.APPROVED, expiry_date__lt=ref_date).count()
        reservations = Reservation.objects.filter(status=ReservationStatus.READY, expiry_date__lt=ref_date).count()
        self.stdout.write(
            f"[dry-run] Would expire {bookings} booking(s), {requests} book request(s), "
            f"{reservations} reservation(s) as of {ref_date}."
        )
