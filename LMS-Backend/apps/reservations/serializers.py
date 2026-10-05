from rest_framework import serializers

from apps.catalogue.models import Book
from apps.members.serializers import RollNumberField
from apps.reservations.models import Reservation


class ReservationSerializer(serializers.ModelSerializer):
    roll_number = serializers.CharField(source="member.roll_number", read_only=True)
    member_name = serializers.CharField(source="member.name", read_only=True)
    held_copy_barcode = serializers.CharField(source="held_copy.barcode", read_only=True, allow_null=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "roll_number",
            "member_name",
            "accession_number",
            "book",
            "book_title",
            "queue_position",
            "status",
            "reserved_date",
            "ready_date",
            "expiry_date",
            "held_copy_barcode",
        ]
        read_only_fields = fields


class ReservationCreateSerializer(serializers.Serializer):
    roll_number = RollNumberField()
    accession_number = serializers.CharField()

    def validate_accession_number(self, value):
        try:
            return Book.objects.get(accession_number__iexact=value)
        except Book.DoesNotExist:
            raise serializers.ValidationError("No book with this accession number.")
