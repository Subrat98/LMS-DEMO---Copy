from rest_framework import serializers

from apps.core.choices import MANUAL_COPY_STATUSES, REASON_REQUIRED_COPY_STATUSES, BookCategory, Classification
from apps.core.serializers import SyllabusTagSerializer
from apps.catalogue.models import Book, BookCopy


class BookSerializer(serializers.ModelSerializer):
    syllabus = SyllabusTagSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "accession_number",
            "title",
            "author",
            "category",
            "classification",
            "subject",
            "price",
            "isbn",
            "publisher",
            "edition",
            "total_copies",
            "available_copies",
            "shelf_location",
            "status",
            "library_use_only",
            "cover_image",
            "acquisition_date",
            "acquisition_source",
            "added_date",
            "syllabus",
        ]
        read_only_fields = ["id", "total_copies", "available_copies", "status", "added_date"]


class BookDetailSerializer(BookSerializer):
    copies = serializers.SerializerMethodField()

    class Meta(BookSerializer.Meta):
        fields = BookSerializer.Meta.fields + ["copies"]

    def get_copies(self, obj):
        return BookCopySerializer(obj.copies.order_by("copy_number"), many=True).data


class BookWriteSerializer(serializers.Serializer):
    accession_number = serializers.CharField(max_length=30)
    title = serializers.CharField(max_length=300)
    author = serializers.CharField(max_length=200)
    category = serializers.ChoiceField(choices=BookCategory.choices)
    classification = serializers.ChoiceField(choices=Classification.choices)
    subject = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    isbn = serializers.CharField(required=False, allow_blank=True)
    publisher = serializers.CharField(required=False, allow_blank=True)
    edition = serializers.CharField(required=False, allow_blank=True)
    total_copies = serializers.IntegerField(min_value=1)
    shelf_location = serializers.CharField(max_length=50)
    library_use_only = serializers.BooleanField(required=False, default=False)
    cover_image = serializers.URLField(required=False, allow_blank=True)
    acquisition_date = serializers.DateField(required=False, allow_null=True)
    acquisition_source = serializers.CharField(required=False, allow_blank=True)
    syllabus = SyllabusTagSerializer(many=True, required=False, allow_null=True)

    def validate_accession_number(self, value):
        qs = Book.objects.filter(accession_number__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A book with this accession number already exists.")
        return value


class BulkImportSerializer(serializers.Serializer):
    file = serializers.FileField()


class AddCopiesSerializer(serializers.Serializer):
    count = serializers.IntegerField(min_value=1, max_value=100)


class CopyStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[(s.value, s.label) for s in MANUAL_COPY_STATUSES])
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["status"] in REASON_REQUIRED_COPY_STATUSES and not attrs.get("reason", "").strip():
            raise serializers.ValidationError(
                {"reason": f"A reason is required to mark a copy as {attrs['status']}."}
            )
        return attrs


class HeldForSerializer(serializers.Serializer):
    kind = serializers.CharField()
    ref = serializers.CharField()
    roll_number = serializers.SerializerMethodField()

    def get_roll_number(self, obj):
        from apps.members.models import Member

        member = Member.objects.filter(pk=obj.member_id).only("roll_number").first()
        return member.roll_number if member else None


class BookCopySerializer(serializers.ModelSerializer):
    accession_number = serializers.CharField(source="book.accession_number", read_only=True)
    held_for = serializers.SerializerMethodField()

    class Meta:
        model = BookCopy
        fields = [
            "id",
            "barcode",
            "accession_number",
            "book",
            "copy_number",
            "status",
            "status_reason",
            "status_changed_date",
            "shelf_location",
            "added_date",
            "held_for",
        ]

    def get_held_for(self, obj):
        from apps.catalogue.services import copy_held_for

        ref = copy_held_for(obj)
        return HeldForSerializer(ref).data if ref else None
