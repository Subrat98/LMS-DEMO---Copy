from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasModulePermission
from apps.library_settings import services
from apps.library_settings.serializers import LibrarySettingsSerializer, PublicSettingsSerializer


class LibrarySettingsView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_permissions = {
        "GET": ("librarySettings", "view"),
        "PUT": ("librarySettings", "edit"),
        "PATCH": ("librarySettings", "edit"),
    }

    def get(self, request):
        return Response(LibrarySettingsSerializer(services.get_settings()).data)

    def put(self, request):
        return self._update(request, partial=False)

    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, partial):
        serializer = LibrarySettingsSerializer(
            services.get_settings(), data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        updated = services.update_settings(serializer.validated_data, actor=request.user)
        return Response(LibrarySettingsSerializer(updated).data)


class PublicSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PublicSettingsSerializer(services.get_settings()).data)
