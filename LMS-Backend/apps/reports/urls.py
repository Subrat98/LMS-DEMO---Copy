from django.urls import path

from apps.reports import views

urlpatterns = [
    path("reports/dashboard-summary/", views.DashboardSummaryView.as_view(), name="report-dashboard-summary"),
    path("reports/holdings/", views.HoldingsReportView.as_view(), name="report-holdings"),
    path(
        "reports/category-distribution/",
        views.CategoryDistributionReportView.as_view(),
        name="report-category-distribution",
    ),
    path(
        "reports/monthly-circulation/",
        views.MonthlyCirculationReportView.as_view(),
        name="report-monthly-circulation",
    ),
    path("reports/department-usage/", views.DepartmentUsageReportView.as_view(), name="report-department-usage"),
    path("reports/overdue/", views.OverdueReportView.as_view(), name="report-overdue"),
    path("reports/top-borrowed/", views.TopBorrowedReportView.as_view(), name="report-top-borrowed"),
    path("reports/fines-breakdown/", views.FinesBreakdownReportView.as_view(), name="report-fines-breakdown"),
    path(
        "reports/reservations-by-status/",
        views.ReservationsByStatusReportView.as_view(),
        name="report-reservations-by-status",
    ),
    path(
        "reports/issue-return-summary/",
        views.IssueReturnSummaryReportView.as_view(),
        name="report-issue-return-summary",
    ),
    path("reports/fine-collection/", views.FineCollectionReportView.as_view(), name="report-fine-collection"),
    path("reports/fine-register/", views.FineRegisterReportView.as_view(), name="report-fine-register"),
    path("reports/clearance/", views.ClearanceReportView.as_view(), name="report-clearance"),
]
