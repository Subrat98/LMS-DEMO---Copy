import django_filters as filters
from django.db.models import Q

from apps.catalogue.models import Book


class BookFilter(filters.FilterSet):
    search = filters.CharFilter(method="filter_search")
    category = filters.CharFilter(field_name="category")
    classification = filters.CharFilter(field_name="classification")
    status = filters.CharFilter(field_name="status")
    library_use_only = filters.BooleanFilter(field_name="library_use_only")
    available = filters.BooleanFilter(method="filter_available")
    accession_number = filters.CharFilter(field_name="accession_number", lookup_expr="iexact")

    class Meta:
        model = Book
        fields = ["category", "classification", "status", "library_use_only", "available", "accession_number"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value)
            | Q(author__icontains=value)
            | Q(accession_number__icontains=value)
            | Q(isbn__icontains=value)
        )

    def filter_available(self, queryset, name, value):
        return queryset.filter(available_copies__gt=0) if value else queryset.filter(available_copies=0)
