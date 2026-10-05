from rest_framework import serializers

from apps.core.choices import Classification
from apps.core.serializers import SyllabusTagSerializer
from apps.ebooks.models import EBook
from apps.ebooks.services import display_file_size


class EBookSerializer(serializers.ModelSerializer):
    syllabus = SyllabusTagSerializer(many=True, required=False, allow_null=True)
    file_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    uploaded_by = serializers.CharField(source="uploaded_by_name", read_only=True)

    class Meta:
        model = EBook
        fields = [
            "id",
            "title",
            "author",
            "classification",
            "file_url",
            "file_size",
            "file_size_bytes",
            "publish_status",
            "description",
            "uploaded_by",
            "uploaded_at",
            "published_at",
            "download_count",
            "syllabus",
        ]
        read_only_fields = [f for f in fields if f not in ("title", "author", "classification", "description", "syllabus")]

    def get_file_url(self, obj):
        request = self.context.get("request")
        path = f"/api/v1/ebooks/{obj.pk}/file/"
        return request.build_absolute_uri(path) if request else path

    def get_file_size(self, obj):
        return display_file_size(obj)


class EBookWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=300)
    author = serializers.CharField(max_length=200)
    classification = serializers.ChoiceField(choices=Classification.choices)
    file = serializers.FileField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    is_published = serializers.BooleanField(required=False, default=False)
    syllabus = SyllabusTagSerializer(many=True, required=False, allow_null=True)

    def validate(self, attrs):
        if self.instance is None and not attrs.get("file"):
            raise serializers.ValidationError({"file": "A file is required when creating an e-book."})
        return attrs
