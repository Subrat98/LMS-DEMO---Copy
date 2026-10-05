from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.serializers import ReasonSerializer
from apps.core.views import BaseStaffViewSet
from apps.members import services
from apps.members.filters import MemberFilter
from apps.members.models import Member
from apps.members.serializers import MemberSerializer, MemberWriteSerializer


class MemberViewSet(BaseStaffViewSet, viewsets.ModelViewSet):
    queryset = Member.objects.with_block_metrics().order_by("roll_number")
    serializer_class = MemberSerializer
    lookup_field = "roll_number"
    lookup_url_kwarg = "roll_number"
    filterset_class = MemberFilter
    search_fields = ["name", "roll_number", "email"]
    ordering_fields = ["roll_number", "name", "join_date"]

    module_permissions = {
        "list": ("members", "view"),
        "retrieve": ("members", "view"),
        "create": ("members", "create"),
        "update": ("members", "edit"),
        "partial_update": ("members", "edit"),
        "destroy": ("members", "delete"),
        "loans": ("members", "view"),
        "fines": ("members", "view"),
        "block": ("members", "edit"),
        "unblock": ("members", "edit"),
        "block_override": ("circulation", "edit"),
        "clearance": ("reports", "view"),
    }

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MemberWriteSerializer
        return MemberSerializer

    def create(self, request, *args, **kwargs):
        serializer = MemberWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        create_login = data.pop("create_login", False)
        password = data.pop("password", None)
        member = services.create_member(data, actor=request.user, create_login=create_login, password=password)
        return Response(MemberSerializer(member).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = MemberWriteSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        data = {k: v for k, v in serializer.validated_data.items() if k not in ("create_login", "password")}
        member = services.update_member(instance, data, actor=request.user)
        return Response(MemberSerializer(member).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        services.delete_member(instance)
        return Response(status=204)

    @action(detail=True, methods=["get"])
    def loans(self, request, roll_number=None):
        from apps.circulation.serializers import LoanSerializer

        member = self.get_object()
        qs = member.loans.all()
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(LoanSerializer(qs.order_by("-issue_date"), many=True).data)

    @action(detail=True, methods=["get"])
    def fines(self, request, roll_number=None):
        from apps.circulation.serializers import FineSerializer

        member = self.get_object()
        return Response(FineSerializer(member.fines.order_by("-created_date"), many=True).data)

    @action(detail=True, methods=["post"])
    def block(self, request, roll_number=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = services.block_member(self.get_object(), serializer.validated_data["reason"], actor=request.user)
        return Response(MemberSerializer(member).data)

    @action(detail=True, methods=["post"])
    def unblock(self, request, roll_number=None):
        member = services.unblock_member(self.get_object(), actor=request.user)
        return Response(MemberSerializer(member).data)

    @action(detail=True, methods=["post", "delete"], url_path="block-override")
    def block_override(self, request, roll_number=None):
        member = self.get_object()
        if request.method == "DELETE":
            member = services.clear_block_override(member, actor=request.user)
        else:
            serializer = ReasonSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            member = services.set_block_override(member, serializer.validated_data["reason"], actor=request.user)
        return Response(MemberSerializer(member).data)

    @action(detail=True, methods=["get"])
    def clearance(self, request, roll_number=None):
        from apps.reports.clearance import compute_clearance

        return Response(compute_clearance(self.get_object()))
