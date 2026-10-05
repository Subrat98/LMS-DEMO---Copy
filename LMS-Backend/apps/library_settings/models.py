from django.db import models


class LibrarySettings(models.Model):
    """Single global settings row (pk is always 1). Ported from `LMS/src/types/settings.ts`."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)

    loan_period_days = models.PositiveSmallIntegerField(default=14)
    max_concurrent_loans = models.PositiveSmallIntegerField(default=2)
    max_renewals_per_loan = models.PositiveSmallIntegerField(default=1)
    fine_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=2)
    max_fine_per_book = models.DecimalField(max_digits=10, decimal_places=2, default=200)
    block_fine_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    block_overdue_days = models.PositiveSmallIntegerField(default=7)
    reservation_hold_days = models.PositiveSmallIntegerField(default=2)
    due_reminder_lead_days = models.PositiveSmallIntegerField(default=2)

    working_hours_open = models.CharField(max_length=5, default="09:30")
    working_hours_close = models.CharField(max_length=5, default="17:30")

    academic_year = models.CharField(max_length=20, default="2026-27")
    college_name = models.CharField(max_length=200, default="Pathani Samanta College")
    college_address = models.CharField(
        max_length=300, default="Khandapara, Nayagarh District, Odisha"
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "Library settings"
        verbose_name_plural = "Library settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("LibrarySettings is a singleton and cannot be deleted.")

    @classmethod
    def load(cls) -> "LibrarySettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Library settings"
