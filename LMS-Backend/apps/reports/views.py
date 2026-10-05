from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasModulePermission
from apps.reports import selectors
from apps.reports.clearance import compute_clearance, compute_clearance_for_members


class BaseReportView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_permissions = {"GET": ("reports", "view")}


class DashboardSummaryView(BaseReportView):
    def get(self, request):
        return Response(selectors.dashboard_summary())


class HoldingsReportView(BaseReportView):
    def get(self, request):
        return Response(selectors.holdings_by_category())


class CategoryDistributionReportView(BaseReportView):
    def get(self, request):
        return Response(selectors.category_distribution())


class MonthlyCirculationReportView(BaseReportView):
    def get(self, request):
        months = int(request.query_params.get("months", 6))
        return Response(selectors.monthly_circulation(months))


class DepartmentUsageReportView(BaseReportView):
    def get(self, request):
        return Response(selectors.department_usage())


class OverdueReportView(BaseReportView):
    def get(self, request):
        limit = int(request.query_params.get("limit", 5))
        return Response({"buckets": selectors.overdue_buckets(), "watchlist": selectors.overdue_watchlist(limit)})


class TopBorrowedReportView(BaseReportView):
    def get(self, request):
        days = int(request.query_params.get("days", 30))
        limit = int(request.query_params.get("limit", 5))
        return Response(selectors.top_borrowed(days, limit))


class FinesBreakdownReportView(BaseReportView):
    def get(self, request):
        return Response(selectors.fines_breakdown())


class ReservationsByStatusReportView(BaseReportView):
    def get(self, request):
        return Response(selectors.reservations_by_status())


class IssueReturnSummaryReportView(BaseReportView):
    def get(self, request):
        return Response(selectors.issue_return_summary())


class FineCollectionReportView(BaseReportView):
    def get(self, request):
        return Response(
            selectors.fine_collection(request.query_params.get("from"), request.query_params.get("to"))
        )


class FineRegisterReportView(BaseReportView):
    def get(self, request):
        params = request.query_params
        rows = selectors.fine_register(
            status=params.get("status"),
            date_from=params.get("from"),
            date_to=params.get("to"),
            roll_number=params.get("rollNumber"),
            department=params.get("department"),
            group_by_student=params.get("groupBy") == "student",
        )
        return Response(rows)


class ClearanceReportView(BaseReportView):
    def get(self, request):
        from apps.members.models import Member

        roll_number = request.query_params.get("rollNumber")
        if roll_number:
            try:
                member = Member.objects.get(roll_number=roll_number)
            except Member.DoesNotExist:
                return Response({"error": {"code": "MEMBER_NOT_FOUND", "message": "No such member."}}, status=404)
            return Response(compute_clearance(member))

        qs = Member.objects.all()
        department = request.query_params.get("department")
        academic_year = request.query_params.get("academicYear")
        if department:
            qs = qs.filter(department=department)
        if academic_year:
            qs = qs.filter(academic_year=academic_year)
        return Response(compute_clearance_for_members(qs))
