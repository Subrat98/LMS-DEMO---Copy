import datetime

import pytest

from apps.circulation.calculators import calculate_due_date, calculate_fine, can_issue_more, can_renew


class FakeSettings:
    loan_period_days = 14
    fine_per_day = 2
    max_fine_per_book = 200
    max_concurrent_loans = 2
    max_renewals_per_loan = 1


def test_fine_is_zero_on_due_date_itself():
    due = datetime.date(2026, 1, 1)
    days, amount = calculate_fine(due, FakeSettings(), ref_date=due)
    assert days == 0
    assert amount == 0


def test_fine_accrues_per_day_after_due_date():
    due = datetime.date(2026, 1, 1)
    ref = datetime.date(2026, 1, 6)
    days, amount = calculate_fine(due, FakeSettings(), ref_date=ref)
    assert days == 5
    assert amount == 10


def test_fine_is_capped_at_max_fine_per_book():
    due = datetime.date(2026, 1, 1)
    ref = due + datetime.timedelta(days=365)
    _, amount = calculate_fine(due, FakeSettings(), ref_date=ref)
    assert amount == FakeSettings.max_fine_per_book


def test_due_date_is_issue_date_plus_loan_period():
    issue = datetime.date(2026, 1, 1)
    assert calculate_due_date(issue, FakeSettings()) == datetime.date(2026, 1, 15)


def test_can_issue_more_is_strict_less_than():
    settings = FakeSettings()
    assert can_issue_more(1, settings) is True
    assert can_issue_more(2, settings) is False


class FakeLoan:
    def __init__(self, status="Active", renewal_count=0):
        self.status = status
        self.renewal_count = renewal_count


def test_can_renew_blocks_closed_loan():
    allowed, reason = can_renew(FakeLoan(status="Returned"), False, FakeSettings())
    assert allowed is False
    assert "closed" in reason.lower()


def test_can_renew_blocks_when_another_member_waiting():
    allowed, reason = can_renew(FakeLoan(), True, FakeSettings())
    assert allowed is False
    assert "waiting" in reason.lower()


def test_can_renew_blocks_after_max_renewals():
    allowed, reason = can_renew(FakeLoan(renewal_count=1), False, FakeSettings())
    assert allowed is False


def test_can_renew_allows_first_renewal():
    allowed, reason = can_renew(FakeLoan(renewal_count=0), False, FakeSettings())
    assert allowed is True
    assert reason is None
