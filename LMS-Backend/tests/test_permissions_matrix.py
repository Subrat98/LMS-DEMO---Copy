import pytest

from apps.core.choices import Role
from apps.core.permissions import PERMISSION_MATRIX, user_can

pytestmark = pytest.mark.django_db

# Representative endpoints for each matrix module, used to spot-check that the
# server-side permission matrix actually gates the real views (not just the pure
# `user_can()` function in isolation).
ENDPOINTS = [
    ("GET", "/api/v1/books/", "books", "view"),
    ("GET", "/api/v1/members/", "members", "view"),
    ("GET", "/api/v1/loans/", "circulation", "view"),
    ("GET", "/api/v1/fines/", "fines", "view"),
    ("GET", "/api/v1/reports/dashboard-summary/", "reports", "view"),
    ("GET", "/api/v1/settings/", "librarySettings", "view"),
    ("GET", "/api/v1/notices/", "notices", "view"),
    ("GET", "/api/v1/bookings/", "bookings", "view"),
    ("GET", "/api/v1/booking-audit/", "bookingAudit", "view"),
]

ROLE_FIXTURES = {
    Role.ADMIN: "admin_user",
    Role.LIBRARIAN: "librarian_user",
    Role.STAFF: "staff_user",
    Role.PRINCIPAL: "principal_user",
}


@pytest.mark.parametrize("method,path,module,action", ENDPOINTS)
@pytest.mark.parametrize("role", list(ROLE_FIXTURES))
def test_endpoint_matches_matrix(request, api_client, role, method, path, module, action):
    user = request.getfixturevalue(ROLE_FIXTURES[role])
    client = api_client(user)
    response = client.get(path)

    expected_allowed = user_can(user, module, action)
    if expected_allowed:
        assert response.status_code in (200, 201), f"{role} should access {path} ({response.status_code})"
    else:
        assert response.status_code == 403, f"{role} should be denied {path} ({response.status_code})"


def test_matrix_has_no_entries_for_student():
    assert PERMISSION_MATRIX[Role.STUDENT] == {}


@pytest.mark.parametrize(
    "role,module,action,expected",
    [
        (Role.ADMIN, "members", "delete", True),
        (Role.LIBRARIAN, "members", "delete", False),
        (Role.STAFF, "books", "create", False),
        (Role.STAFF, "circulation", "create", True),
        (Role.PRINCIPAL, "circulation", "view", False),
        (Role.PRINCIPAL, "reports", "view", True),
        (Role.LIBRARIAN, "bookings", "create", True),
        (Role.ADMIN, "bookings", "create", False),
    ],
)
def test_matrix_literal_values(role, module, action, expected):
    assert (action in PERMISSION_MATRIX[role].get(module, frozenset())) is expected
