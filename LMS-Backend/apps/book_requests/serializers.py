from rest_framework import serializers

from apps.book_requests.models import BookRequest
from apps.core.serializers import OptionalReasonSerializer


class BookRequestSerializer(serializers.ModelSerializer):
    roll_number = serializers.CharField(source="member.roll_number", read_only=True)
    member_name = serializers.CharField(source="member.name", read_only=True)
    held_copy_barcode = serializers.CharField(source="held_copy.barcode", read_only=True, allow_null=True)
    loan_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = BookRequest
        fields = [
            "id",
            "roll_number",
            "member_name",
            "accession_number",
            "book",
            "book_title",
            "requested_date",
            "status",
            "held_copy_barcode",
            "ready_date",
            "expiry_date",
            "reject_reason",
            "loan_id",
        ]
        read_only_fields = fields


RejectSerializer = OptionalReasonSerializer
