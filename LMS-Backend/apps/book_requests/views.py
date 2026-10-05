from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.book_requests import services
from apps.book_requests.models import BookRequest
from apps.book_requests.serializers import BookRequestSerializer, RejectSerializer
from apps.core.views import BaseStaffViewSet


class BookRequestViewSet(BaseStaffViewSet, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = BookRequest.objects.select_related("member", "held_copy").all()
    serializer_class = BookRequestSerializer
    filterset_fields = ["status"]
    module_permissions = {
        "list": ("circulation", "view"),
        "approve": ("circulation", "create"),
        "reject": ("circulation", "create"),
        "cancel": ("circulation", "create"),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        roll_number = self.request.query_params.get("rollNumber")
        if roll_number:
            qs = qs.filter(member__roll_number=roll_number)
        return qs.order_by("requested_date")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        req = services.approve_request(self.get_object(), actor=request.user)
        return Response(BookRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = services.reject_request(self.get_object(), serializer.validated_data.get("reason", ""), actor=request.user)
        return Response(BookRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        req = services.cancel_request(self.get_object(), actor=request.user)
        return Response(BookRequestSerializer(req).data)
