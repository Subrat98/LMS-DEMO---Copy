"""Date helpers ported from `LMS/src/utils/date.ts`.

The frontend's `todayISO()`/`overdueDays()` pair is the single source of truth for every
due-date and fine calculation in the app; this module is the server-side equivalent.
"""

from django.utils import timezone


def today():
    """Local calendar date "today" (matches the frontend's `todayISO()`)."""
    return timezone.localdate()


def add_days(value, days: int):
    from datetime import timedelta

    return value + timedelta(days=days)


def is_overdue(due_date, ref_date=None) -> bool:
    ref_date = ref_date or today()
    return due_date < ref_date


def overdue_days(due_date, ref_date=None) -> int:
    """0 if not overdue (the due date itself is not overdue); else calendar days late."""
    ref_date = ref_date or today()
    if not is_overdue(due_date, ref_date):
        return 0
    return (ref_date - due_date).days
