"""Ported from `LMS/src/utils/clearance.ts` — a member is cleared only when every book is
returned, every fine is paid or waived, and no copy is held for them.
"""

from apps.core.choices import OPEN_BOOKING_STATUSES, LoanStatus, RequestStatus, ReservationStatus, FineStatus
from apps.core.dates import overdue_days, today


def compute_clearance(member) -> dict:
    from apps.bookings.models import Booking
    from apps.book_requests.models import BookRequest
    from apps.circulation.models import Fine, Loan
    from apps.reservations.models import Reservation

    active_loans = list(Loan.objects.filter(member=member, status=LoanStatus.ACTIVE))
    overdue_loans = [loan for loan in active_loans if overdue_days(loan.due_date) > 0]
    pending_fines = list(Fine.objects.filter(member=member, status=FineStatus.PENDING))
    pending_fine_total = sum(float(fine.amount) for fine in pending_fines)

    held_items = [
        {"kind": "Booking", "ref": b.booking_no, "bookTitle": b.book_title}
        for b in Booking.objects.filter(member=member, status__in=OPEN_BOOKING_STATUSES)
    ] + [
        {"kind": "Request", "ref": r.held_copy.barcode if r.held_copy else str(r.pk), "bookTitle": r.book_title}
        for r in BookRequest.objects.filter(member=member, status=RequestStatus.APPROVED)
    ] + [
        {"kind": "Reservation", "ref": str(r.pk), "bookTitle": r.book_title}
        for r in Reservation.objects.filter(member=member, status=ReservationStatus.READY)
    ]

    dues = []
    if active_loans:
        suffix = f" ({len(overdue_loans)} overdue)" if overdue_loans else ""
        dues.append(f"{len(active_loans)} book(s) not returned{suffix}")
    if pending_fines:
        dues.append(f"Unpaid fines ₹{pending_fine_total:.0f} ({len(pending_fines)})")
    if held_items:
        dues.append(f"{len(held_items)} copy/copies held (booking / request / reservation)")

    cleared = len(dues) == 0
    result = {
        "rollNumber": member.roll_number,
        "name": member.name,
        "department": member.department,
        "academicYear": member.academic_year,
        "cleared": cleared,
        "activeLoans": [
            {"bookTitle": l.book_title, "dueDate": l.due_date.isoformat(), "copyBarcode": l.copy_barcode}
            for l in active_loans
        ],
        "overdueLoans": [l.id for l in overdue_loans],
        "pendingFines": [
            {"bookTitle": f.book_title, "overdueDays": f.overdue_days, "amount": float(f.amount)}
            for f in pending_fines
        ],
        "pendingFineTotal": pending_fine_total,
        "heldItems": held_items,
        "dues": dues,
    }
    if cleared:
        result["certificateNo"] = f"CLR-{today():%Y%m%d}-{member.roll_number}"
    return result


def compute_clearance_for_members(members) -> list[dict]:
    return [compute_clearance(m) for m in members]
