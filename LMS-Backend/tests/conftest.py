import pytest
from rest_framework.test import APIClient

from apps.core.choices import Role
from apps.core.dates import today


@pytest.fixture
def settings_obj(db):
    from apps.library_settings.services import get_settings

    return get_settings()


@pytest.fixture
def make_user(db):
    from apps.accounts.models import User

    def _make(username, role, member=None, password="password123"):
        user = User.objects.create_user(username=username, name=username.title(), role=role, member=member)
        user.set_password(password)
        user.save()
        return user

    return _make


@pytest.fixture
def make_member(db):
    from apps.members.models import Member

    counter = {"n": 0}

    def _make(roll_number=None, department="B.Sc. Physics", academic_year="1st Year", **extra):
        counter["n"] += 1
        roll_number = roll_number or f"TEST{counter['n']:04d}"
        defaults = {
            "name": f"Test Member {counter['n']}",
            "department": department,
            "academic_year": academic_year,
            "email": f"test{counter['n']}@example.com",
            "phone": "9000000000",
            "status": "Active",
            "join_date": today(),
        }
        defaults.update(extra)
        return Member.objects.create(roll_number=roll_number, **defaults)

    return _make


@pytest.fixture
def make_book(db):
    from apps.catalogue import services as catalogue_services

    counter = {"n": 0}

    def _make(total_copies=2, category="Science", classification="Stream - Science", **extra):
        counter["n"] += 1
        data = {
            "accession_number": f"TST-{counter['n']:04d}",
            "title": f"Test Book {counter['n']}",
            "author": "Test Author",
            "category": category,
            "classification": classification,
            "subject": "Testing",
            "price": 100,
            "shelf_location": "T1",
            "library_use_only": False,
            "total_copies": total_copies,
        }
        data.update(extra)
        return catalogue_services.create_book(data)

    return _make


@pytest.fixture
def admin_user(make_user):
    return make_user("admin_test", Role.ADMIN)


@pytest.fixture
def librarian_user(make_user):
    return make_user("librarian_test", Role.LIBRARIAN)


@pytest.fixture
def staff_user(make_user):
    return make_user("staff_test", Role.STAFF)


@pytest.fixture
def principal_user(make_user):
    return make_user("principal_test", Role.PRINCIPAL)


@pytest.fixture
def student_member(make_member):
    return make_member(roll_number="2030001")


@pytest.fixture
def student_user(make_user, student_member):
    return make_user("2030001", Role.STUDENT, member=student_member)


@pytest.fixture
def api_client():
    def _client(user=None):
        client = APIClient()
        if user is not None:
            from rest_framework_simplejwt.tokens import RefreshToken

            token = RefreshToken.for_user(user)
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return client

    return _client
