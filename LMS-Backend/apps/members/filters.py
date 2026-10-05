import django_filters as filters
from django.db.models import Q

from apps.members.models import Member


class MemberFilter(filters.FilterSet):
    search = filters.CharFilter(method="filter_search")
    department = filters.CharFilter(field_name="department")
    academic_year = filters.CharFilter(field_name="academic_year")
    status = filters.CharFilter(field_name="status")
    blocked = filters.BooleanFilter(field_name="is_blocked")

    class Meta:
        model = Member
        fields = ["department", "academic_year", "status", "blocked"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(roll_number__icontains=value) | Q(email__icontains=value)
        )
