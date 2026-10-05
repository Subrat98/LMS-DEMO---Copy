from rest_framework import serializers

from apps.bookings.models import Booking, BookingAuditEntry
from apps.catalogue.models import Book
from apps.core.dates import today
from apps.members.serializers import RollNumberField


class BookingSerializer(serializers.ModelSerializer):
    roll_number = serializers.CharField(source="member.roll_number", read_only=True)
    held_copy_barcode = serializers.CharField(source="held_copy.barcode", read_only=True, allow_null=True)
    loan_id = serializers.IntegerField(read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_no",
            "roll_number",
            "student_name",
            "accession_number",
            "book",
            "book_title",
            "booking_date",
            "expiry_date",
            "status",
            "held_copy_barcode",
            "updated_at",
            "verified_by_name",
            "verified_at",
            "issued_by_name",
            "issued_at",
            "loan_id",
            "returned_at",
            "cancelled_by_name",
            "cancelled_at",
            "cancellation_reason",
            "is_expired",
        ]
        read_only_fields = fields

    def get_is_expired(self, obj):
        return obj.status in ("Booked", "Verified") and obj.expiry_date < today()


class BookingCreateSerializer(serializers.Serializer):
    roll_number = RollNumberField()
    accession_number = serializers.CharField()

    def validate_accession_number(self, value):
        try:
            return Book.objects.get(accession_number__iexact=value)
        except Book.DoesNotExist:
            raise serializers.ValidationError("No book with this accession number.")


class BookingUpdateSerializer(serializers.Serializer):
    accession_number = serializers.CharField()

    def validate_accession_number(self, value):
        try:
            return Book.objects.get(accession_number__iexact=value)
        except Book.DoesNotExist:
            raise serializers.ValidationError("No book with this accession number.")


class BookingLookupSerializer(serializers.Serializer):
    booking_no = serializers.CharField()
    roll_number = serializers.CharField(required=False, allow_blank=True)


class BookingAuditSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = BookingAuditEntry
        fields = [
            "id",
            "user_id",
            "user_name",
            "role",
            "action_time",
            "action",
            "booking_no",
            "cancellation_reason",
            "details",
        ]
        read_only_fields = fields
