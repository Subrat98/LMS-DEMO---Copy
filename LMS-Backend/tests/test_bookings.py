import pytest
from django.core.exceptions import PermissionDenied

from apps.bookings import services as booking_services
from apps.core.exceptions import BusinessRuleError

pytestmark = pytest.mark.django_db


def test_booking_numbers_are_sequential_and_never_reused(student_member, make_book):
    b1 = booking_services.create_booking(student_member, make_book())
    b2 = booking_services.create_booking(student_member, make_book())
    assert b1.booking_no != b2.booking_no
    seq1 = int(b1.booking_no.split("-")[-1])
    seq2 = int(b2.booking_no.split("-")[-1])
    assert seq2 == seq1 + 1

    booking_services.cancel_booking(b2, None, "test cancel", system=True)
    b3 = booking_services.create_booking(student_member, make_book())
    assert int(b3.booking_no.split("-")[-1]) == seq2 + 1  # never reused, even after cancel


def test_booking_counts_against_the_same_cap_as_loans(student_member, make_book, settings_obj):
    for _ in range(settings_obj.max_concurrent_loans):
        booking_services.create_booking(student_member, make_book())
    with pytest.raises(BusinessRuleError) as exc:
        booking_services.create_booking(student_member, make_book())
    assert exc.value.code == "BOOKING_LIMIT_REACHED"


def test_booking_out_of_stream_is_rejected(student_member, make_book):
    # student_member is B.Sc. Physics (Science stream); Commerce/Course book is a different stream
    book = make_book(category="Commerce", classification="Course")
    with pytest.raises(BusinessRuleError) as exc:
        booking_services.create_booking(student_member, book)
    assert exc.value.code == "OUT_OF_STREAM"


def test_cancel_releases_the_held_copy(student_member, make_book):
    book = make_book(total_copies=1)
    booking = booking_services.create_booking(student_member, book)
    book.refresh_from_db()
    assert book.available_copies == 0

    booking_services.cancel_booking(booking, None, "test", system=True)
    book.refresh_from_db()
    assert book.available_copies == 1


def test_verify_then_issue_creates_a_loan(student_member, make_book):
    book = make_book()
    booking = booking_services.create_booking(student_member, book)
    booking_services.verify_booking(booking.booking_no, None, actor=None)
    booking, loan = booking_services.issue_booking(booking.booking_no, None, actor=None)
    assert booking.status == "Issued"
    assert loan.status == "Active"
    assert loan.member_id == student_member.id


def test_lookup_rejects_cancelled_booking(student_member, make_book):
    booking = booking_services.create_booking(student_member, make_book())
    booking_services.cancel_booking(booking, None, "test", system=True)
    with pytest.raises(BusinessRuleError) as exc:
        booking_services.lookup_booking(booking.booking_no)
    assert exc.value.code == "BOOKING_CANCELLED"


def test_audit_entries_are_append_only(student_member, make_book):
    from apps.bookings.models import BookingAuditEntry

    booking_services.create_booking(student_member, make_book())
    entry = BookingAuditEntry.objects.first()
    with pytest.raises(PermissionDenied):
        entry.action = "Update"
        entry.save()
    with pytest.raises(PermissionDenied):
        entry.delete()
