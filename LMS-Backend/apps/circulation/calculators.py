"""Pure calculation functions, no database access — ported from
`LMS/src/utils/fineCalculator.ts` and `LMS/src/utils/loanCalculator.ts`.
"""

from apps.core.choices import LoanStatus
from apps.core.dates import add_days, overdue_days


def calculate_fine(due_date, settings, ref_date=None) -> tuple[int, float]:
    days = overdue_days(due_date, ref_date)
    amount = min(days * float(settings.fine_per_day), float(settings.max_fine_per_book))
    return days, amount


def calculate_due_date(issue_date, settings):
    return add_days(issue_date, settings.loan_period_days)


def calculate_renewed_due_date(loan, settings):
    """Extends from the loan's CURRENT due date, not from today."""
    return add_days(loan.due_date, settings.loan_period_days)


def can_issue_more(active_loan_count: int, settings) -> bool:
    return active_loan_count < settings.max_concurrent_loans


def can_renew(loan, has_pending_reservation: bool, settings) -> tuple[bool, str | None]:
    if loan.status != LoanStatus.ACTIVE:
        raise_reason = "This loan is already closed."
        return False, raise_reason
    if has_pending_reservation:
        return False, "Another member is waiting for this title (FR-REN-02)."
    if loan.renewal_count >= settings.max_renewals_per_loan:
        return False, "This loan has already been renewed the maximum number of times (FR-REN-01)."
    return True, None
