from rest_framework import serializers

from apps.core.dates import today
from apps.notices.models import Notice


class NoticeSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Notice
        fields = [
            "id",
            "title",
            "content",
            "category",
            "publish_date",
            "expiry_date",
            "created_by_name",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = ["id", "created_by_name", "created_at", "updated_at", "is_active"]

    def get_is_active(self, obj):
        ref = today()
        return obj.publish_date <= ref and (obj.expiry_date is None or obj.expiry_date >= ref)

    def validate(self, attrs):
        publish_date = attrs.get("publish_date", getattr(self.instance, "publish_date", None))
        expiry_date = attrs.get("expiry_date", getattr(self.instance, "expiry_date", None))
        if expiry_date and publish_date and expiry_date < publish_date:
            raise serializers.ValidationError({"expiry_date": "Expiry date must be on or after the publish date."})
        return attrs
