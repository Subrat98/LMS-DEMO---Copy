from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.circulation import services
from apps.circulation.calculators import calculate_fine
from apps.circulation.filters import FineFilter, LoanFilter
from apps.circulation.models import Fine, Loan
from apps.circulation.serializers import (
    FineDetailSerializer,
    FineSerializer,
    IssueSerializer,
    LoanSerializer,
    ReturnByBarcodeSerializer,
)
from apps.core.dates import today
from apps.core.serializers import ReasonSerializer
from apps.core.views import BaseStaffViewSet
from apps.library_settings.services import get_settings


class LoanViewSet(
    BaseStaffViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = Loan.objects.select_related("member", "book", "copy").all()
    serializer_class = LoanSerializer
    filterset_class = LoanFilter
    module_permissions = {
        "list": ("circulation", "view"),
        "retrieve": ("circulation", "view"),
        "active": ("circulation", "view"),
        "returned": ("circulation", "view"),
        "overdue": ("circulation", "view"),
        "transactions": ("circulation", "view"),
        "issue": ("circulation", "create"),
        "return_loan": ("circulation", "edit"),
        "return_by_barcode": ("circulation", "edit"),
        "return_preview": ("circulation", "edit"),
        "renew": ("circulation", "edit"),
    }

    @action(detail=False, methods=["get"])
    def active(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(status="Active"))
        return self._list(qs)

    @action(detail=False, methods=["get"])
    def returned(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(status="Returned").order_by("-return_date"))
        return self._list(qs)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        qs = self.filter_queryset(
            self.get_queryset().filter(status="Active", due_date__lt=today()).order_by("due_date")
        )
        return self._list(qs)

    @action(detail=False, methods=["get"])
    def transactions(self, request):
        limit = int(request.query_params.get("limit", 50))
        qs = self.get_queryset().order_by("-issue_date")[:limit]
        return Response(LoanSerializer(qs, many=True).data)

    def _list(self, qs):
        page = self.paginate_queryset(qs)
        serializer = LoanSerializer(page if page is not None else qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=False, methods=["post"])
    def issue(self, request):
        serializer = IssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        loan = services.issue_book(
            member=serializer.validated_data["roll_number"],
            book=serializer.validated_data["accession_number"],
            copy_barcode=serializer.validated_data.get("copy_barcode") or None,
            actor=request.user,
        )
        return Response(LoanSerializer(loan).data, status=201)

    @action(detail=True, methods=["get"], url_path="return-preview")
    def return_preview(self, request, pk=None):
        loan = self.get_object()
        settings = get_settings()
        days, amount = calculate_fine(loan.due_date, settings)
        return Response({"overdueDays": days, "fineAmount": amount})

    @action(detail=True, methods=["post"], url_path="return")
    def return_loan(self, request, pk=None):
        result = services.return_book(self.get_object(), actor=request.user)
        return Response(
            {
                "loan": LoanSerializer(result.loan).data,
                "fineAmount": result.fine_amount,
                "fine": FineSerializer(result.fine).data if result.fine else None,
                "reservationPromoted": result.promoted_reservation is not None,
            }
        )

    @action(detail=False, methods=["post"], url_path="return-by-barcode")
    def return_by_barcode(self, request):
        serializer = ReturnByBarcodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.return_by_barcode(serializer.validated_data["copy_barcode"], actor=request.user)
        return Response(
            {
                "loan": LoanSerializer(result.loan).data,
                "fineAmount": result.fine_amount,
                "fine": FineSerializer(result.fine).data if result.fine else None,
                "reservationPromoted": result.promoted_reservation is not None,
            }
        )

    @action(detail=True, methods=["post"])
    def renew(self, request, pk=None):
        loan = services.renew_loan(self.get_object(), actor=request.user)
        return Response(LoanSerializer(loan).data)


class FineViewSet(BaseStaffViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Fine.objects.select_related("member", "loan", "actioned_by").all()
    filterset_class = FineFilter
    module_permissions = {
        "list": ("fines", "view"),
        "retrieve": ("fines", "view"),
        "collect": ("fines", "edit"),
        "waive": ("fines", "edit"),
    }

    def get_serializer_class(self):
        return FineDetailSerializer if self.action == "retrieve" else FineSerializer

    @action(detail=True, methods=["post"])
    def collect(self, request, pk=None):
        fine = services.collect_fine(self.get_object(), actor=request.user)
        return Response(FineSerializer(fine).data)

    @action(detail=True, methods=["post"])
    def waive(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fine = services.waive_fine(self.get_object(), serializer.validated_data["reason"], actor=request.user)
        return Response(FineSerializer(fine).data)
