"""Server-side authorization, ported 1:1 from `LMS/src/access/permissions.ts`.

The frontend's permission matrix was enforced only in the browser (hiding buttons/routes),
which is not a security boundary. Every staff endpoint here re-checks the same matrix
against `request.user.role`, read fresh from the database on every request.
"""

from rest_framework.permissions import BasePermission

from apps.core.choices import STAFF_ROLES, Role

MODULES = (
    "books",
    "circulation",
    "members",
    "reservations",
    "fines",
    "reports",
    "librarySettings",
    "notices",
    "bookings",
    "bookingAudit",
)
ACTIONS = ("view", "create", "edit", "delete")

# Literal copy of buildDefaultMatrix() in permissions.ts.
PERMISSION_MATRIX: dict[str, dict[str, frozenset[str]]] = {
    Role.ADMIN: {
        "books": frozenset({"view", "create", "edit", "delete"}),
        "circulation": frozenset({"view", "create", "edit"}),
        "members": frozenset({"view", "create", "edit", "delete"}),
        "reservations": frozenset({"view", "create", "edit"}),
        "fines": frozenset({"view", "edit"}),
        "reports": frozenset({"view"}),
        "librarySettings": frozenset({"view", "edit"}),
        "notices": frozenset({"view", "create", "edit", "delete"}),
        "bookings": frozenset({"view", "edit"}),
        "bookingAudit": frozenset({"view"}),
    },
    Role.LIBRARIAN: {
        "books": frozenset({"view", "create", "edit", "delete"}),
        "circulation": frozenset({"view", "create", "edit"}),
        "members": frozenset({"view", "create", "edit"}),
        "reservations": frozenset({"view", "create", "edit"}),
        "fines": frozenset({"view", "edit"}),
        "reports": frozenset({"view"}),
        "notices": frozenset({"view", "create", "edit", "delete"}),
        "bookings": frozenset({"view", "edit", "create"}),
        "bookingAudit": frozenset({"view"}),
    },
    Role.STAFF: {
        "books": frozenset({"view"}),
        "circulation": frozenset({"view", "create", "edit"}),
        "reservations": frozenset({"view", "create", "edit"}),
        "fines": frozenset({"view"}),
        "notices": frozenset({"view"}),
    },
    Role.PRINCIPAL: {
        "books": frozenset({"view"}),
        "fines": frozenset({"view"}),
        "reports": frozenset({"view"}),
        "notices": frozenset({"view"}),
        "bookings": frozenset({"view", "edit"}),
        "bookingAudit": frozenset({"view"}),
    },
    Role.STUDENT: {},
}


def user_can(user, module: str, action: str = "view") -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    role_perms = PERMISSION_MATRIX.get(user.role, {})
    return action in role_perms.get(module, frozenset())


class HasModulePermission(BasePermission):
    """Views set `module_permissions = {<viewset action or HTTP method>: (module, action)}`.

    A missing key means deny (fail closed) rather than silently allowing an unmapped action.
    An entry may also be a `{HTTP_METHOD: (module, action)}` dict, for a single action (e.g. one
    @action decorated with methods=["get", "post"]) that needs a different permission per method.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.role not in STAFF_ROLES or user.status != "active":
            return False

        module_permissions = getattr(view, "module_permissions", None)
        if not module_permissions:
            return False

        key = getattr(view, "action", None) or request.method
        if key not in module_permissions:
            return False

        entry = module_permissions[key]
        if isinstance(entry, dict):
            entry = entry.get(request.method)
            if entry is None:
                return False

        module, action = entry
        return user_can(user, module, action)


class IsStudentWithMember(BasePermission):
    """Gates the whole `student` self-service app."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.role == Role.STUDENT and user.status == "active" and user.member_id is not None


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.ADMIN)
