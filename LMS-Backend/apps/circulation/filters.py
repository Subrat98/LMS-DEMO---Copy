import django_filters as filters
from django.db.models import Q

from apps.circulation.models import Loan


class LoanFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    roll_number = filters.CharFilter(field_name="member__roll_number")
    accession_number = filters.CharFilter(field_name="accession_number", lookup_expr="iexact")
    issue_date_after = filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issue_date_before = filters.DateFilter(field_name="issue_date", lookup_expr="lte")
    search = filters.CharFilter(method="filter_search")
    overdue = filters.BooleanFilter(method="filter_overdue")
    issued_today = filters.BooleanFilter(method="filter_issued_today")
    due_today = filters.BooleanFilter(method="filter_due_today")

    class Meta:
        model = Loan
        fields = ["status", "roll_number", "accession_number"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(book_title__icontains=value)
            | Q(member__name__icontains=value)
            | Q(member__roll_number__icontains=value)
        )

    def filter_overdue(self, queryset, name, value):
        from apps.core.dates import today

        if value:
            return queryset.filter(status="Active", due_date__lt=today())
        return queryset

    def filter_issued_today(self, queryset, name, value):
        from apps.core.dates import today

        return queryset.filter(issue_date=today()) if value else queryset

    def filter_due_today(self, queryset, name, value):
        from apps.core.dates import today

        return queryset.filter(status="Active", due_date=today()) if value else queryset


class FineFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    roll_number = filters.CharFilter(field_name="member__roll_number")
    date_after = filters.DateFilter(field_name="created_date", lookup_expr="gte")
    date_before = filters.DateFilter(field_name="created_date", lookup_expr="lte")
    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, name, value):
        return queryset.filter(Q(member_name__icontains=value) | Q(book_title__icontains=value))
