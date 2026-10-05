from django.db import models

from apps.core.choices import RequestStatus


class BookRequest(models.Model):
    """Student 'apply to borrow a currently-available title' — simpler parallel flow to Booking.

    Note the deliberate asymmetry vs Booking: open BookRequests do NOT count against
    `maxConcurrentLoans` the way open Bookings do (ported from the frontend as-is).
    """

    member = models.ForeignKey("members.Member", on_delete=models.PROTECT, related_name="book_requests")
    book = models.ForeignKey("catalogue.Book", on_delete=models.PROTECT, related_name="book_requests")
    accession_number = models.CharField(max_length=30)
    book_title = models.CharField(max_length=300)
    requested_date = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=12, choices=RequestStatus.choices, default=RequestStatus.PENDING, db_index=True
    )

    held_copy = models.ForeignKey(
        "catalogue.BookCopy", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    ready_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    reject_reason = models.CharField(max_length=300, blank=True)
    loan = models.OneToOneField(
        "circulation.Loan", null=True, blank=True, on_delete=models.SET_NULL, related_name="fulfilled_request"
    )
    actioned_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        indexes = [
            models.Index(fields=["member", "status"]),
            models.Index(fields=["status", "expiry_date"]),
        ]
        ordering = ["requested_date"]

    def __str__(self):
        return f"BookRequest({self.member.roll_number}, {self.book_title}, {self.status})"
