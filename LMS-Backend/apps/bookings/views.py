from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.bookings import services
from apps.bookings.filters import BookingAuditFilter, BookingFilter
from apps.bookings.models import Booking, BookingAuditEntry
from apps.bookings.serializers import (
    BookingAuditSerializer,
    BookingCreateSerializer,
    BookingLookupSerializer,
    BookingSerializer,
)
from apps.circulation.serializers import LoanSerializer
from apps.core.serializers import ReasonSerializer
from apps.core.views import BaseStaffViewSet


class BookingViewSet(
    BaseStaffViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = Booking.objects.select_related("member", "book", "held_copy").all()
    serializer_class = BookingSerializer
    filterset_class = BookingFilter
    lookup_field = "booking_no"
    lookup_url_kwarg = "booking_no"
    module_permissions = {
        "list": ("bookings", "view"),
        "retrieve": ("bookings", "view"),
        "create": ("bookings", "create"),
        "lookup": ("bookings", "create"),
        "verify": ("bookings", "create"),
        "issue": ("bookings", "create"),
        "cancel": ("bookings", "edit"),
    }

    def get_queryset(self):
        return super().get_queryset().order_by("-booking_date")

    def create(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = services.create_booking(
            serializer.validated_data["roll_number"], serializer.validated_data["accession_number"], actor=request.user
        )
        return Response(BookingSerializer(booking).data, status=201)

    @action(detail=False, methods=["post"])
    def lookup(self, request):
        serializer = BookingLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = services.lookup_booking(
            serializer.validated_data["booking_no"], serializer.validated_data.get("roll_number") or None
        )
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def verify(self, request, booking_no=None):
        serializer = BookingLookupSerializer(data={**request.data, "booking_no": booking_no})
        serializer.is_valid(raise_exception=True)
        booking = services.verify_booking(booking_no, serializer.validated_data.get("roll_number") or None, request.user)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def issue(self, request, booking_no=None):
        roll_number = request.data.get("rollNumber") or request.data.get("roll_number")
        booking, loan = services.issue_booking(booking_no, roll_number, request.user)
        return Response({"booking": BookingSerializer(booking).data, "loan": LoanSerializer(loan).data})

    @action(detail=True, methods=["post"])
    def cancel(self, request, booking_no=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = services.cancel_booking(self.get_object(), request.user, serializer.validated_data["reason"])
        return Response(BookingSerializer(booking).data)


class BookingAuditViewSet(BaseStaffViewSet, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = BookingAuditEntry.objects.all()
    serializer_class = BookingAuditSerializer
    filterset_class = BookingAuditFilter
    module_permissions = {"list": ("bookingAudit", "view")}
