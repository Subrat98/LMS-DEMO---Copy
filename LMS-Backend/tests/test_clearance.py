import pytest

from apps.circulation import services as circulation_services
from apps.reports.clearance import compute_clearance

pytestmark = pytest.mark.django_db


def test_member_with_no_history_is_cleared(student_member):
    status = compute_clearance(student_member)
    assert status["cleared"] is True
    assert status["dues"] == []
    assert status["certificateNo"].startswith("CLR-")


def test_active_loan_blocks_clearance(student_member, make_book):
    circulation_services.issue_book(member=student_member, book=make_book())
    status = compute_clearance(student_member)
    assert status["cleared"] is False
    assert any("not returned" in due for due in status["dues"])


def test_pending_fine_blocks_clearance(student_member, make_book):
    from apps.circulation.models import Fine

    Fine.objects.create(
        loan=circulation_services.issue_book(member=student_member, book=make_book()),
        member=student_member,
        member_name=student_member.name,
        book_title="x",
        overdue_days=5,
        amount=50,
        status="Pending",
        created_date="2026-01-01",
    )
    status = compute_clearance(student_member)
    assert status["cleared"] is False
    assert status["pendingFineTotal"] == 50


def test_clearing_the_loan_and_fine_restores_cleared_status(student_member, make_book):
    loan = circulation_services.issue_book(member=student_member, book=make_book())
    result = circulation_services.return_book(loan)
    assert compute_clearance(student_member)["cleared"] is True
    if result.fine:
        circulation_services.collect_fine(result.fine)
    assert compute_clearance(student_member)["cleared"] is True
