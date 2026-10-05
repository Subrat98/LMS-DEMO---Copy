from rest_framework import serializers

from apps.core.choices import AcademicYear, Department, MemberStatus
from apps.library_settings.services import get_settings
from apps.members.models import Member


class RollNumberField(serializers.SlugRelatedField):
    """Looks up a Member by roll_number — the only "member ID" the API exposes."""

    default_error_messages = {
        "does_not_exist": "No member with roll number '{value}'.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("slug_field", "roll_number")
        kwargs.setdefault("queryset", Member.objects.all())
        super().__init__(**kwargs)


class BlockOverrideSerializer(serializers.Serializer):
    overridden_by = serializers.IntegerField(source="block_override_by_id", allow_null=True)
    overridden_by_name = serializers.CharField(source="block_override_by_name")
    reason = serializers.CharField(source="block_override_reason")
    overridden_at = serializers.DateTimeField(source="block_override_at")


class BlockStatusSerializer(serializers.Serializer):
    is_blocked = serializers.BooleanField()
    is_overridden = serializers.BooleanField()
    reasons = serializers.ListField(child=serializers.CharField())
    primary_reason = serializers.CharField(allow_null=True)
    pending_fine_total = serializers.FloatField()
    max_overdue_days = serializers.IntegerField()


class MemberSerializer(serializers.ModelSerializer):
    block_override = serializers.SerializerMethodField()
    block_status = serializers.SerializerMethodField()
    active_loan_count = serializers.SerializerMethodField()
    has_login = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id",
            "roll_number",
            "name",
            "department",
            "academic_year",
            "email",
            "phone",
            "status",
            "is_blocked",
            "block_reason",
            "block_override",
            "block_status",
            "active_loan_count",
            "has_login",
            "join_date",
            "avatar_url",
        ]
        read_only_fields = ["id"]

    def get_block_override(self, obj):
        if not obj.has_block_override:
            return None
        return BlockOverrideSerializer(obj).data

    def get_block_status(self, obj):
        from apps.members.services import evaluate_block_status

        pending_fine_total = getattr(obj, "pending_fine_total", None)
        max_overdue = overdue_from_annotation(obj)
        status = evaluate_block_status(
            obj, get_settings(), pending_fine_total=pending_fine_total, max_overdue=max_overdue
        )
        return BlockStatusSerializer(status).data

    def get_active_loan_count(self, obj):
        value = getattr(obj, "active_loan_count", None)
        if value is not None:
            return value
        return obj.loans.filter(status="Active").count()

    def get_has_login(self, obj):
        return hasattr(obj, "user") and obj.user is not None


def overdue_from_annotation(member) -> int | None:
    """`with_block_metrics()` annotates `oldest_active_due`; convert it to overdue days here.

    Returns None (meaning "not annotated, compute live") when the member wasn't loaded via
    `with_block_metrics()`; returns 0 when it was annotated but has no active loans.
    """
    if not hasattr(member, "oldest_active_due"):
        return None
    oldest_due = member.oldest_active_due
    if oldest_due is None:
        return 0
    from apps.core.dates import overdue_days

    return overdue_days(oldest_due)


class MemberWriteSerializer(serializers.Serializer):
    """Create/update. `rollNumber` required and unique (case-insensitive); immutable once issued
    is NOT enforced here (the frontend disabled the input, but renaming is a valid admin action —
    `members.services.update_member` keeps the linked login's username in sync).
    """

    roll_number = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=150)
    department = serializers.ChoiceField(choices=Department.choices)
    academic_year = serializers.ChoiceField(choices=AcademicYear.choices)
    email = serializers.EmailField()
    phone = serializers.RegexField(r"^\d{10}$", error_messages={"invalid": "Enter a valid 10-digit phone number."})
    status = serializers.ChoiceField(choices=MemberStatus.choices, default=MemberStatus.ACTIVE)
    create_login = serializers.BooleanField(required=False, default=False, write_only=True)
    password = serializers.CharField(required=False, write_only=True, allow_blank=True)

    def validate_roll_number(self, value):
        qs = Member.objects.filter(roll_number__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A member with this roll number already exists.")
        return value
