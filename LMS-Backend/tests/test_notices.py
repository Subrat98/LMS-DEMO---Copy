import pytest

from apps.core.dates import add_days, today

pytestmark = pytest.mark.django_db


@pytest.fixture
def notices(db):
    from apps.notices.models import Notice

    live = Notice.objects.create(
        title="Live notice", content="x", category="Events", publish_date=add_days(today(), -1)
    )
    scheduled = Notice.objects.create(
        title="Scheduled notice", content="x", category="Events", publish_date=add_days(today(), 5)
    )
    expired = Notice.objects.create(
        title="Expired notice",
        content="x",
        category="Circulars",
        publish_date=add_days(today(), -30),
        expiry_date=add_days(today(), -1),
    )
    return {"live": live, "scheduled": scheduled, "expired": expired}


def test_student_sees_only_live_notices(api_client, student_user, notices):
    client = api_client(student_user)
    response = client.get("/api/v1/student/notices/")
    assert response.status_code == 200
    titles = {n["title"] for n in response.json()}
    assert titles == {"Live notice"}


def test_staff_sees_all_notices_by_default(api_client, librarian_user, notices):
    client = api_client(librarian_user)
    response = client.get("/api/v1/notices/")
    assert response.status_code == 200
    titles = {n["title"] for n in response.json()["results"]}
    assert titles == {"Live notice", "Scheduled notice", "Expired notice"}


def test_staff_can_filter_to_active_only(api_client, librarian_user, notices):
    client = api_client(librarian_user)
    response = client.get("/api/v1/notices/?active=true")
    titles = {n["title"] for n in response.json()["results"]}
    assert titles == {"Live notice"}


def test_staff_view_only_role_cannot_create_notice(api_client, staff_user):
    client = api_client(staff_user)
    response = client.post(
        "/api/v1/notices/",
        {"title": "x", "content": "x", "category": "Events", "publishDate": str(today())},
        format="json",
    )
    assert response.status_code == 403


def test_librarian_can_create_notice_and_created_by_is_server_assigned(api_client, librarian_user):
    client = api_client(librarian_user)
    response = client.post(
        "/api/v1/notices/",
        {"title": "New notice", "content": "body", "category": "Events", "publishDate": str(today())},
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["createdByName"] == librarian_user.name

    from apps.notices.models import Notice

    notice = Notice.objects.get(pk=body["id"])
    assert notice.created_by_id == librarian_user.id


def test_expiry_before_publish_is_rejected(api_client, librarian_user):
    client = api_client(librarian_user)
    response = client.post(
        "/api/v1/notices/",
        {
            "title": "Bad dates",
            "content": "x",
            "category": "Events",
            "publishDate": str(today()),
            "expiryDate": str(add_days(today(), -5)),
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_student_cannot_access_staff_notices_endpoint(api_client, student_user):
    client = api_client(student_user)
    response = client.get("/api/v1/notices/")
    assert response.status_code == 403
