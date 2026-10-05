from django.db import models

from apps.core.choices import ReservationStatus


class Reservation(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.PROTECT, related_name="reservations")
    book = models.ForeignKey("catalogue.Book", on_delete=models.PROTECT, related_name="reservations")
    accession_number = models.CharField(max_length=30)
    book_title = models.CharField(max_length=300)
    queue_position = models.PositiveIntegerField()
    status = models.CharField(
        max_length=12, choices=ReservationStatus.choices, default=ReservationStatus.WAITING, db_index=True
    )
    reserved_date = models.DateField(auto_now_add=True)
    ready_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    # Fixes a frontend gap: knowing exactly which copy is held for this reservation,
    # instead of releasing "any Held copy" on expiry/cancel.
    held_copy = models.ForeignKey(
        "catalogue.BookCopy", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    loan = models.OneToOneField(
        "circulation.Loan", null=True, blank=True, on_delete=models.SET_NULL, related_name="fulfilled_reservation"
    )

    class Meta:
        indexes = [models.Index(fields=["book", "status", "queue_position"])]
        ordering = ["queue_position"]

    def __str__(self):
        return f"Reservation({self.member.roll_number}, {self.book_title}, {self.status})"
