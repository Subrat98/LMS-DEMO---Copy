from rest_framework import serializers

from apps.catalogue.models import Book
from apps.circulation.models import Fine, Loan
from apps.members.serializers import RollNumberField


class LoanSerializer(serializers.ModelSerializer):
    roll_number = serializers.CharField(source="member.roll_number", read_only=True)
    member_name = serializers.CharField(source="member.name", read_only=True)
    department = serializers.CharField(source="member.department", read_only=True)
    book_id = serializers.IntegerField(read_only=True)
    fine_id = serializers.SerializerMethodField()
    booking_id = serializers.SerializerMethodField()
    overdue_days = serializers.SerializerMethodField()
    accrued_fine = serializers.SerializerMethodField()
    can_renew = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            "id",
            "roll_number",
            "member_name",
            "department",
            "accession_number",
            "book_id",
            "book_title",
            "copy_barcode",
            "issue_date",
            "due_date",
            "return_date",
            "status",
            "renewal_count",
            "fine_id",
            "booking_id",
            "overdue_days",
            "accrued_fine",
            "can_renew",
        ]
        read_only_fields = fields

    def get_fine_id(self, obj):
        fine = getattr(obj, "fine", None)
        return fine.id if fine is not None else None

    def get_booking_id(self, obj):
        return obj.booking.id if hasattr(obj, "booking") else None

    def get_overdue_days(self, obj):
        from apps.core.dates import overdue_days

        if obj.status != "Active":
            return 0
        return overdue_days(obj.due_date)

    def get_accrued_fine(self, obj):
        if obj.status != "Active":
            return 0
        from apps.circulation.calculators import calculate_fine
        from apps.library_settings.services import get_settings

        _, amount = calculate_fine(obj.due_date, get_settings())
        return amount

    def get_can_renew(self, obj):
        if obj.status != "Active":
            return {"allowed": False, "reason": "This loan is already closed."}
        from apps.circulation.calculators import can_renew
        from apps.library_settings.services import get_settings
        from apps.reservations.services import has_pending_reservation

        settings = get_settings()
        allowed, reason = can_renew(obj, has_pending_reservation(obj.book), settings)
        return {"allowed": allowed, "reason": reason}


class FineSerializer(serializers.ModelSerializer):
    roll_number = serializers.CharField(source="member.roll_number", read_only=True)
    loan_id = serializers.IntegerField(read_only=True)
    actioned_by_name = serializers.CharField(source="actioned_by.name", read_only=True, allow_null=True)

    class Meta:
        model = Fine
        fields = [
            "id",
            "loan_id",
            "roll_number",
            "member_name",
            "book_title",
            "overdue_days",
            "amount",
            "reason",
            "status",
            "created_date",
            "collected_date",
            "actioned_by_name",
        ]
        read_only_fields = fields


class FineDetailSerializer(FineSerializer):
    loan = LoanSerializer(read_only=True)

    class Meta(FineSerializer.Meta):
        fields = FineSerializer.Meta.fields + ["loan"]


class IssueSerializer(serializers.Serializer):
    roll_number = RollNumberField()
    accession_number = serializers.CharField()
    copy_barcode = serializers.CharField(required=False, allow_blank=True)

    def validate_accession_number(self, value):
        try:
            return Book.objects.get(accession_number__iexact=value)
        except Book.DoesNotExist:
            raise serializers.ValidationError("No book with this accession number.")

    def validate_copy_barcode(self, value):
        return value.strip().upper() if value else value


class ReturnByBarcodeSerializer(serializers.Serializer):
    copy_barcode = serializers.CharField()
