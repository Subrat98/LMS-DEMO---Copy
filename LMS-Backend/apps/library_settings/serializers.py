import re

from rest_framework import serializers

_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


class WorkingHoursSerializer(serializers.Serializer):
    open = serializers.CharField(allow_blank=False)
    close = serializers.CharField(allow_blank=False)

    def validate_open(self, value):
        return _validate_time(value)

    def validate_close(self, value):
        return _validate_time(value)


def _validate_time(value: str) -> str:
    if not _TIME_RE.match(value):
        raise serializers.ValidationError("Must be in HH:MM form, e.g. 09:30.")
    return value


class LibrarySettingsSerializer(serializers.Serializer):
    """Full read/write shape. Validation ranges match `LMS/src/utils/validators/settingsSchema.ts`."""

    loan_period_days = serializers.IntegerField(min_value=1, max_value=90)
    max_concurrent_loans = serializers.IntegerField(min_value=1, max_value=10)
    max_renewals_per_loan = serializers.IntegerField(min_value=0, max_value=5)
    fine_per_day = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, max_value=100)
    max_fine_per_book = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, max_value=5000)
    block_fine_threshold = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, max_value=10000
    )
    block_overdue_days = serializers.IntegerField(min_value=1, max_value=90)
    reservation_hold_days = serializers.IntegerField(min_value=1, max_value=14)
    due_reminder_lead_days = serializers.IntegerField(min_value=1, max_value=14)
    working_hours = WorkingHoursSerializer()
    academic_year = serializers.CharField(allow_blank=False)
    college_name = serializers.CharField(allow_blank=False)
    college_address = serializers.CharField(allow_blank=False)
    updated_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        return {
            "loan_period_days": instance.loan_period_days,
            "max_concurrent_loans": instance.max_concurrent_loans,
            "max_renewals_per_loan": instance.max_renewals_per_loan,
            "fine_per_day": instance.fine_per_day,
            "max_fine_per_book": instance.max_fine_per_book,
            "block_fine_threshold": instance.block_fine_threshold,
            "block_overdue_days": instance.block_overdue_days,
            "reservation_hold_days": instance.reservation_hold_days,
            "due_reminder_lead_days": instance.due_reminder_lead_days,
            "working_hours": {"open": instance.working_hours_open, "close": instance.working_hours_close},
            "academic_year": instance.academic_year,
            "college_name": instance.college_name,
            "college_address": instance.college_address,
            "updated_at": instance.updated_at,
        }


class PublicSettingsSerializer(serializers.Serializer):
    """Subset exposed to any signed-in user (students need loan/fine policy, not college address edit rights)."""

    loan_period_days = serializers.IntegerField(read_only=True)
    max_concurrent_loans = serializers.IntegerField(read_only=True)
    max_renewals_per_loan = serializers.IntegerField(read_only=True)
    fine_per_day = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    max_fine_per_book = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    reservation_hold_days = serializers.IntegerField(read_only=True)
    academic_year = serializers.CharField(read_only=True)
    college_name = serializers.CharField(read_only=True)
    college_address = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        return {
            "loan_period_days": instance.loan_period_days,
            "max_concurrent_loans": instance.max_concurrent_loans,
            "max_renewals_per_loan": instance.max_renewals_per_loan,
            "fine_per_day": instance.fine_per_day,
            "max_fine_per_book": instance.max_fine_per_book,
            "reservation_hold_days": instance.reservation_hold_days,
            "working_hours": {"open": instance.working_hours_open, "close": instance.working_hours_close},
            "academic_year": instance.academic_year,
            "college_name": instance.college_name,
            "college_address": instance.college_address,
        }
