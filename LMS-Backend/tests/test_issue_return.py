import pytest

from apps.circulation import services as circulation_services
from apps.core.dates import add_days
from apps.core.exceptions import BusinessRuleError

pytestmark = pytest.mark.django_db


def test_issue_book_creates_active_loan_and_marks_copy_issued(student_member, make_book):
    book = make_book(total_copies=1)
    loan = circulation_services.issue_book(member=student_member, book=book)
    assert loan.status == "Active"
    book.refresh_from_db()
    assert book.available_copies == 0
    assert book.copies.first().status == "Issued"


def test_issue_book_blocked_at_loan_limit(student_member, make_book, settings_obj):
    for _ in range(settings_obj.max_concurrent_loans):
        circulation_services.issue_book(member=student_member, book=make_book())
    with pytest.raises(BusinessRuleError) as exc:
        circulation_services.issue_book(member=student_member, book=make_book())
    assert exc.value.code == "LOAN_LIMIT_REACHED"


def test_issue_book_blocked_for_retired_book(student_member, make_book):
    from apps.catalogue import services as catalogue_services

    book = make_book()
    catalogue_services.retire_book(book)
    with pytest.raises(BusinessRuleError) as exc:
        circulation_services.issue_book(member=student_member, book=book)
    assert exc.value.code == "BOOK_RETIRED"


def test_issue_book_blocked_for_library_use_only(student_member, make_book):
    book = make_book(library_use_only=True)
    with pytest.raises(BusinessRuleError) as exc:
        circulation_services.issue_book(member=student_member, book=book)
    assert exc.value.code == "LIBRARY_USE_ONLY"


def test_return_on_time_creates_no_fine(student_member, make_book):
    book = make_book()
    loan = circulation_services.issue_book(member=student_member, book=book)
    result = circulation_services.return_book(loan)
    assert result.fine_amount == 0
    assert result.fine is None
    loan.refresh_from_db()
    assert loan.status == "Returned"
    book.refresh_from_db()
    assert book.available_copies == book.total_copies


def test_return_late_creates_pending_fine(student_member, make_book, settings_obj):
    book = make_book()
    loan = circulation_services.issue_book(member=student_member, book=book)
    loan.due_date = add_days(loan.issue_date, -5)  # already overdue by "issue time"
    loan.save(update_fields=["due_date"])
    result = circulation_services.return_book(loan)
    assert result.fine_amount > 0
    assert result.fine.status == "Pending"


def test_cannot_return_an_already_returned_loan(student_member, make_book):
    loan = circulation_services.issue_book(member=student_member, book=make_book())
    circulation_services.return_book(loan)
    with pytest.raises(BusinessRuleError) as exc:
        circulation_services.return_book(loan)
    assert exc.value.code == "LOAN_ALREADY_RETURNED"


def test_renew_extends_due_date_and_blocks_second_renewal(student_member, make_book, settings_obj):
    book = make_book()
    loan = circulation_services.issue_book(member=student_member, book=book)
    original_due = loan.due_date
    loan = circulation_services.renew_loan(loan)
    assert loan.due_date == add_days(original_due, settings_obj.loan_period_days)
    assert loan.renewal_count == 1

    with pytest.raises(BusinessRuleError) as exc:
        circulation_services.renew_loan(loan)
    assert exc.value.code == "RENEWAL_BLOCKED"


def test_member_blocked_by_fine_threshold_cannot_borrow(student_member, make_book, settings_obj):
    from apps.circulation.models import Fine

    Fine.objects.create(
        loan=circulation_services.issue_book(member=student_member, book=make_book()),
        member=student_member,
        member_name=student_member.name,
        book_title="x",
        overdue_days=10,
        amount=float(settings_obj.block_fine_threshold) + 1,
        status="Pending",
        created_date="2026-01-01",
    )
    with pytest.raises(BusinessRuleError) as exc:
        circulation_services.issue_book(member=student_member, book=make_book())
    assert exc.value.code == "MEMBER_BLOCKED"


def test_duplicate_title_blocked_across_loan_and_booking(student_member, make_book):
    book = make_book(total_copies=5)
    circulation_services.issue_book(member=student_member, book=book)
    with pytest.raises(BusinessRuleError) as exc:
        circulation_services.assert_no_duplicate_title(student_member, book)
    assert exc.value.code == "DUPLICATE_TITLE"
