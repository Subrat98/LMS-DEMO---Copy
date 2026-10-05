from django.core.exceptions import PermissionDenied
from django.db import models

from apps.core.choices import AuditAction, BookingStatus


class Booking(models.Model):
    booking_no = models.CharField(max_length=20, unique=True)
    member = models.ForeignKey("members.Member", on_delete=models.PROTECT, related_name="bookings")
    student_name = models.CharField(max_length=150)
    book = models.ForeignKey("catalogue.Book", on_delete=models.PROTECT, related_name="bookings")
    accession_number = models.CharField(max_length=30)
    book_title = models.CharField(max_length=300)

    booking_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    status = models.CharField(max_length=10, choices=BookingStatus.choices, default=BookingStatus.BOOKED, db_index=True)
    held_copy = models.ForeignKey(
        "catalogue.BookCopy", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    verified_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    verified_by_name = models.CharField(max_length=150, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    issued_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    issued_by_name = models.CharField(max_length=150, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    loan = models.OneToOneField(
        "circulation.Loan", null=True, blank=True, on_delete=models.SET_NULL, related_name="booking"
    )

    returned_at = models.DateTimeField(null=True, blank=True)

    cancelled_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    cancelled_by_name = models.CharField(max_length=150, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["member", "status"]),
            models.Index(fields=["status", "expiry_date"]),
        ]
        ordering = ["-booking_date"]

    def __str__(self):
        return self.booking_no


class BookingSequence(models.Model):
    year = models.PositiveSmallIntegerField(primary_key=True)
    last_seq = models.PositiveIntegerField(default=0)


class AppendOnlyQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        raise PermissionDenied("Booking audit entries are append-only and cannot be deleted.")

    def update(self, *args, **kwargs):
        raise PermissionDenied("Booking audit entries are append-only and cannot be modified.")


AppendOnlyManager = models.Manager.from_queryset(AppendOnlyQuerySet)


class BookingAuditEntry(models.Model):
    """Append-only: save() refuses to overwrite an existing row, delete is blocked."""

    booking_no = models.CharField(max_length=20, db_index=True)  # not an FK: audits outlive any booking issue
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    user_name = models.CharField(max_length=150)
    role = models.CharField(max_length=12)  # Role choices, plus the literal 'system'

    action_time = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=10, choices=AuditAction.choices)
    cancellation_reason = models.CharField(max_length=300, blank=True)
    details = models.CharField(max_length=300, blank=True)

    objects = AppendOnlyManager()

    class Meta:
        ordering = ["-action_time"]
        indexes = [models.Index(fields=["booking_no"])]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionDenied("Booking audit entries are append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Booking audit entries are append-only and cannot be deleted.")

    def __str__(self):
        return f"{self.booking_no}: {self.action}"
