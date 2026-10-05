import csv
import io

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.views import BaseStaffViewSet
from apps.catalogue import services
from apps.catalogue.filters import BookFilter
from apps.catalogue.models import Book, BookCopy
from apps.catalogue.serializers import (
    AddCopiesSerializer,
    BookDetailSerializer,
    BookSerializer,
    BookWriteSerializer,
    BulkImportSerializer,
    CopyStatusSerializer,
    BookCopySerializer,
)

BULK_IMPORT_COLUMNS = [
    "AccessionNumber",
    "Title",
    "Author",
    "Subject",
    "Classification",
    "Publisher",
    "Edition",
    "ISBN",
    "Price",
    "Copies",
    "ShelfLocation",
    "LibraryUseOnly",
]


class BookViewSet(BaseStaffViewSet, viewsets.ModelViewSet):
    queryset = Book.objects.all()
    filterset_class = BookFilter
    search_fields = ["title", "author", "accession_number", "isbn"]
    ordering_fields = ["title", "added_date", "available_copies"]

    module_permissions = {
        "list": ("books", "view"),
        "retrieve": ("books", "view"),
        "create": ("books", "create"),
        "update": ("books", "edit"),
        "partial_update": ("books", "edit"),
        "destroy": ("books", "delete"),
        "retire": ("books", "edit"),
        "reinstate": ("books", "edit"),
        "bulk_import": ("books", "create"),
        "bulk_import_template": ("books", "create"),
        "copies": {"GET": ("books", "view"), "POST": ("books", "edit")},
    }

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return BookWriteSerializer
        if self.action == "retrieve":
            return BookDetailSerializer
        return BookSerializer

    def create(self, request, *args, **kwargs):
        serializer = BookWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = services.create_book(dict(serializer.validated_data), actor=request.user)
        return Response(BookDetailSerializer(book).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = BookWriteSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        book = services.update_book(instance, dict(serializer.validated_data), actor=request.user)
        return Response(BookDetailSerializer(book).data)

    def destroy(self, request, *args, **kwargs):
        services.delete_book(self.get_object())
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        book = services.retire_book(self.get_object(), actor=request.user)
        return Response(BookSerializer(book).data)

    @action(detail=True, methods=["post"])
    def reinstate(self, request, pk=None):
        book = services.reinstate_book(self.get_object(), actor=request.user)
        return Response(BookSerializer(book).data)

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        serializer = BulkImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.bulk_import_books(serializer.validated_data["file"], actor=request.user)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="bulk-import/template")
    def bulk_import_template(self, request):
        buffer = io.StringIO()
        csv.writer(buffer).writerow(BULK_IMPORT_COLUMNS)
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="book-import-template.csv"'
        return response

    @action(detail=True, methods=["get", "post"])
    def copies(self, request, pk=None):
        book = self.get_object()
        if request.method == "POST":
            serializer = AddCopiesSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_copies = services.add_copies(book, serializer.validated_data["count"], actor=request.user)
            return Response(BookCopySerializer(new_copies, many=True).data, status=201)
        return Response(BookCopySerializer(book.copies.order_by("copy_number"), many=True).data)


def _get_copy(barcode: str) -> BookCopy:
    return get_object_or_404(BookCopy, barcode=barcode.strip().upper())


class CopyDetailView(APIView):
    permission_classes = BaseStaffViewSet.permission_classes
    module_permissions = {"GET": ("books", "view")}

    def get(self, request, barcode):
        return Response(BookCopySerializer(_get_copy(barcode)).data)


class CopyStatusView(APIView):
    permission_classes = BaseStaffViewSet.permission_classes
    module_permissions = {"PATCH": ("books", "edit")}

    def patch(self, request, barcode):
        copy = _get_copy(barcode)
        serializer = CopyStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = services.change_copy_status_manual(
            copy, serializer.validated_data["status"], serializer.validated_data.get("reason", ""), actor=request.user
        )
        return Response(BookCopySerializer(updated).data)
