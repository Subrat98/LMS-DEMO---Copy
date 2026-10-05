from django.db import models
from django.db.models import Count, Min, Q, Sum

from apps.core.choices import AcademicYear, Department, MemberStatus


class MemberQuerySet(models.QuerySet):
    def with_block_metrics(self):
        """Annotates fields `evaluate_block_status()` needs, avoiding N+1 queries on list views."""
        from apps.core.choices import FineStatus, LoanStatus

        return self.annotate(
            pending_fine_total=Sum(
                "fines__amount", filter=Q(fines__status=FineStatus.PENDING), default=0
            ),
            oldest_active_due=Min("loans__due_date", filter=Q(loans__status=LoanStatus.ACTIVE)),
            active_loan_count=Count(
                "loans", filter=Q(loans__status=LoanStatus.ACTIVE), distinct=True
            ),
        )


class Member(models.Model):
    """A student / library-card holder. `roll_number` is the ONE business identifier —
    the frontend's separate `MEM-xxxx` memberId scheme is deliberately dropped.
    """

    roll_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    department = models.CharField(max_length=40, choices=Department.choices, db_index=True)
    academic_year = models.CharField(max_length=20, choices=AcademicYear.choices)
    email = models.EmailField()
    phone = models.CharField(max_length=10)
    status = models.CharField(
        max_length=12, choices=MemberStatus.choices, default=MemberStatus.ACTIVE, db_index=True
    )

    is_blocked = models.BooleanField(default=False)
    block_reason = models.TextField(blank=True)

    block_override_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    block_override_by_name = models.CharField(max_length=150, blank=True)
    block_override_reason = models.TextField(blank=True)
    block_override_at = models.DateTimeField(null=True, blank=True)

    join_date = models.DateField()
    avatar_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MemberQuerySet.as_manager()

    class Meta:
        ordering = ["roll_number"]

    def __str__(self):
        return f"{self.roll_number} — {self.name}"

    @property
    def has_block_override(self) -> bool:
        return self.block_override_reason != ""
