from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import HasModulePermission, IsStudentWithMember


class BaseStaffViewSet:
    """Mixin (combine with a DRF viewset): sets `module_permissions = {action_or_method: (module, action)}`.

    Plain mixin rather than a GenericViewSet subclass, so it composes cleanly with
    `viewsets.ModelViewSet`/`ReadOnlyModelViewSet` without an MRO clash.
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_permissions: dict = {}


class BaseStudentView(GenericAPIView):
    """Every student self-service view is scoped to `self.member` (never another student's data)."""

    permission_classes = [IsStudentWithMember]

    @property
    def member(self):
        return self.request.user.member
