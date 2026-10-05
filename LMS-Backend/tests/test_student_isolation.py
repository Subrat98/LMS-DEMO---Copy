import pytest

pytestmark = pytest.mark.django_db


def test_student_cannot_see_another_students_loans(api_client, make_member, make_user, make_book):
    from apps.circulation import services as circulation_services
    from apps.core.choices import Role

    member_a = make_member(roll_number="2031001")
    member_b = make_member(roll_number="2031002")
    user_a = make_user("2031001", Role.STUDENT, member=member_a)
    make_user("2031002", Role.STUDENT, member=member_b)

    circulation_services.issue_book(member=member_b, book=make_book())

    client = api_client(user_a)
    response = client.get("/api/v1/student/loans/")
    assert response.status_code == 200
    assert response.json() == []  # student A sees none of student B's loans


def test_student_cannot_cancel_another_students_booking(api_client, make_member, make_user, make_book):
    from apps.bookings import services as booking_services
    from apps.core.choices import Role

    member_a = make_member(roll_number="2032001")
    member_b = make_member(roll_number="2032002")
    user_a = make_user("2032001", Role.STUDENT, member=member_a)
    make_user("2032002", Role.STUDENT, member=member_b)

    booking = booking_services.create_booking(member_b, make_book())

    client = api_client(user_a)
    response = client.post(f"/api/v1/student/bookings/{booking.booking_no}/cancel/", {}, format="json")
    assert response.status_code == 404  # not found, not 403 — queryset-level isolation


def test_staff_endpoint_rejects_student_role(api_client, student_user):
    client = api_client(student_user)
    response = client.get("/api/v1/members/")
    assert response.status_code == 403


def test_unauthenticated_request_is_rejected(api_client):
    client = api_client()
    response = client.get("/api/v1/student/me/")
    assert response.status_code == 401
