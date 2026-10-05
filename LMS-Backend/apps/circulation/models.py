from django.db import models

from apps.core.choices import FineStatus, LoanStatus


class Loan(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.PROTECT, related_name="loans")
    book = models.ForeignKey("catalogue.Book", on_delete=models.PROTECT, related_name="loans")
    copy = models.ForeignKey("catalogue.BookCopy", on_delete=models.PROTECT, related_name="loans")

    # Snapshots so history survives later renumbering/renaming.
    book_title = models.CharField(max_length=300)
    accession_number = models.CharField(max_length=30)
    copy_barcode = models.CharField(max_length=40)

    issue_date = models.DateField()
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=LoanStatus.choices, default=LoanStatus.ACTIVE, db_index=True)
    renewal_count = models.PositiveSmallIntegerField(default=0)

    issued_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    returned_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        indexes = [
            models.Index(fields=["member", "status"]),
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["book", "status"]),
        ]
        ordering = ["-issue_date"]

    def __str__(self):
        return f"Loan({self.member.roll_number}, {self.book_title}, {self.status})"


class Fine(models.Model):
    loan = models.OneToOneField(Loan, on_delete=models.PROTECT, related_name="fine")
    member = models.ForeignKey("members.Member", on_delete=models.PROTECT, related_name="fines")

    member_name = models.CharField(max_length=150)
    book_title = models.CharField(max_length=300)

    overdue_days = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True)  # also holds the waive reason
    status = models.CharField(max_length=10, choices=FineStatus.choices, default=FineStatus.PENDING, db_index=True)

    created_date = models.DateField()
    collected_date = models.DateField(null=True, blank=True)
    actioned_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        indexes = [
            models.Index(fields=["member", "status"]),
            models.Index(fields=["status", "collected_date"]),
        ]
        ordering = ["-created_date"]

    def __str__(self):
        return f"Fine({self.member.roll_number}, {self.amount}, {self.status})"
