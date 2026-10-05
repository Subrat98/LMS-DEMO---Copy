from rest_framework import serializers

from apps.catalogue.models import Book
from apps.core.serializers import SyllabusTagSerializer


class StudentBookSerializer(serializers.ModelSerializer):
    """Drops price/acquisition fields the frontend never showed students, and adds
    booking/request eligibility hints so the UI doesn't have to re-derive them.
    """

    syllabus = SyllabusTagSerializer(many=True, read_only=True)
    is_on_syllabus = serializers.SerializerMethodField()

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
            "total_copies",
            "available_copies",
            "status",
            "library_use_only",
            "cover_image",
            "syllabus",
            "is_on_syllabus",
        ]
        read_only_fields = fields

    def get_is_on_syllabus(self, obj):
        from apps.core.stream import is_on_syllabus

        member = self.context["member"]
        return is_on_syllabus(obj.syllabus, member)
