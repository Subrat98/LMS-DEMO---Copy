from django.db.models import Q
from django.http import FileResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.views import BaseStaffViewSet
from apps.ebooks import services
from apps.ebooks.models import EBook
from apps.ebooks.serializers import EBookSerializer, EBookWriteSerializer


class EBookViewSet(BaseStaffViewSet, viewsets.ModelViewSet):
    queryset = EBook.objects.all()
    filterset_fields = ["publish_status", "classification"]
    module_permissions = {
        "list": ("books", "view"),
        "retrieve": ("books", "view"),
        "create": ("books", "create"),
        "update": ("books", "edit"),
        "partial_update": ("books", "edit"),
        "destroy": ("books", "delete"),
        "publish": ("books", "edit"),
        "file": ("books", "view"),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(author__icontains=search) | Q(classification__icontains=search))
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EBookWriteSerializer
        return EBookSerializer

    def create(self, request, *args, **kwargs):
        serializer = EBookWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ebook = services.create_ebook(dict(serializer.validated_data), actor=request.user)
        return Response(EBookSerializer(ebook, context={"request": request}).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = EBookWriteSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        ebook = services.update_ebook(instance, dict(serializer.validated_data), actor=request.user)
        return Response(EBookSerializer(ebook, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        services.delete_ebook(self.get_object())
        return Response(status=204)

    def retrieve(self, request, *args, **kwargs):
        return Response(EBookSerializer(self.get_object(), context={"request": request}).data)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        serializer = EBookSerializer(page if page is not None else qs, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        is_published = bool(request.data.get("isPublished") or request.data.get("is_published"))
        ebook = services.toggle_publish_status(self.get_object(), is_published)
        return Response(EBookSerializer(ebook, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        ebook = self.get_object()
        return FileResponse(ebook.file.open("rb"), filename=ebook.file.name.split("/")[-1])
