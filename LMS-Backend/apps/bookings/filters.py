import django_filters as filters
from django.db.models import Q

from apps.bookings.models import Booking, BookingAuditEntry


class BookingFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    roll_number = filters.CharFilter(field_name="member__roll_number")
    date_after = filters.DateFilter(field_name="booking_date", lookup_expr="gte")
    date_before = filters.DateFilter(field_name="booking_date", lookup_expr="lte")
    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(booking_no__icontains=value) | Q(student_name__icontains=value) | Q(book_title__icontains=value)
        )


class BookingAuditFilter(filters.FilterSet):
    booking_no = filters.CharFilter(field_name="booking_no", lookup_expr="icontains")
    action = filters.CharFilter(field_name="action")
    role = filters.CharFilter(field_name="role")
    date_after = filters.DateFilter(field_name="action_time", lookup_expr="gte")
    date_before = filters.DateFilter(field_name="action_time", lookup_expr="lte")

    class Meta:
        model = BookingAuditEntry
        fields = ["booking_no", "action", "role"]
