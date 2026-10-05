from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.views import BaseStaffViewSet
from apps.reservations import services
from apps.reservations.models import Reservation
from apps.reservations.serializers import ReservationCreateSerializer, ReservationSerializer


class ReservationViewSet(
    BaseStaffViewSet, mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = Reservation.objects.select_related("member", "held_copy").all()
    serializer_class = ReservationSerializer
    filterset_fields = ["status", "accession_number"]
    module_permissions = {
        "list": ("reservations", "view"),
        "create": ("reservations", "create"),
        "cancel": ("reservations", "edit"),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        roll_number = self.request.query_params.get("rollNumber")
        if roll_number:
            qs = qs.filter(member__roll_number=roll_number)
        return qs.order_by("-reserved_date")

    def create(self, request, *args, **kwargs):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = services.reserve(
            serializer.validated_data["roll_number"], serializer.validated_data["accession_number"], actor=request.user
        )
        return Response(ReservationSerializer(reservation).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        reservation = services.cancel_reservation(self.get_object(), actor=request.user)
        return Response(ReservationSerializer(reservation).data)
