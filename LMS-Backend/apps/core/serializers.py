from rest_framework import serializers

from apps.core.choices import AcademicYear, Department


class SyllabusTagSerializer(serializers.Serializer):
    programme = serializers.ChoiceField(choices=Department.choices)
    year = serializers.ChoiceField(choices=AcademicYear.choices)


class ReasonSerializer(serializers.Serializer):
    """Shared shape for every 'give a reason' action: waive fine, block override, cancel booking."""

    reason = serializers.CharField(allow_blank=False, trim_whitespace=True)

    def validate_reason(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A reason is required.")
        return value


class OptionalReasonSerializer(serializers.Serializer):
    """Like ReasonSerializer, but the reason is optional (e.g. rejecting a book request)."""

    reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
