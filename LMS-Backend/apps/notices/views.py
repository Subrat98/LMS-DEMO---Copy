from rest_framework import viewsets

from apps.core.dates import today
from apps.core.views import BaseStaffViewSet
from apps.notices.models import Notice
from apps.notices.serializers import NoticeSerializer


class NoticeViewSet(BaseStaffViewSet, viewsets.ModelViewSet):
    serializer_class = NoticeSerializer
    filterset_fields = ["category"]
    module_permissions = {
        "list": ("notices", "view"),
        "retrieve": ("notices", "view"),
        "create": ("notices", "create"),
        "update": ("notices", "edit"),
        "partial_update": ("notices", "edit"),
        "destroy": ("notices", "delete"),
    }

    def get_queryset(self):
        qs = Notice.objects.all()
        if self.request.query_params.get("active") == "true":
            ref = today()
            qs = qs.filter(publish_date__lte=ref).exclude(expiry_date__lt=ref)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, created_by_name=self.request.user.name or self.request.user.username)
