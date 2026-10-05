from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.core.dates import overdue_days
from apps.core.exceptions import BusinessRuleError
from apps.members.models import Member


@dataclass
class BlockStatus:
    is_blocked: bool
    is_overridden: bool
    reasons: list[str] = field(default_factory=list)
    primary_reason: str | None = None
    pending_fine_total: float = 0
    max_overdue_days: int = 0


def evaluate_block_status(member: Member, settings, *, pending_fine_total=None, max_overdue=None) -> BlockStatus:
    """Ported from `LMS/src/utils/blockChecker.ts` — three independent triggers, not short-circuited."""
    reasons: list[str] = []

    if member.is_blocked and member.block_reason:
        reasons.append(f"Manually blocked: {member.block_reason}")

    if pending_fine_total is None:
        from django.db.models import Sum

        from apps.circulation.models import Fine  # local import: avoids a members<->circulation cycle
        from apps.core.choices import FineStatus

        pending_fine_total = (
            Fine.objects.filter(member=member, status=FineStatus.PENDING).aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )
    pending_fine_total = float(pending_fine_total or 0)
    if pending_fine_total > float(settings.block_fine_threshold):
        reasons.append(f"Outstanding fines of ₹{pending_fine_total:.0f} exceed the ₹{settings.block_fine_threshold:.0f} threshold")

    if max_overdue is None:
        from apps.circulation.models import Loan
        from apps.core.choices import LoanStatus

        max_overdue = 0
        for loan in Loan.objects.filter(member=member, status=LoanStatus.ACTIVE).only("due_date"):
            days = overdue_days(loan.due_date)
            if days > max_overdue:
                max_overdue = days
    if max_overdue > settings.block_overdue_days:
        reasons.append(f"A book is {max_overdue} day(s) overdue (limit {settings.block_overdue_days})")

    return BlockStatus(
        is_blocked=len(reasons) > 0,
        is_overridden=member.has_block_override,
        reasons=reasons,
        primary_reason=reasons[0] if reasons else None,
        pending_fine_total=pending_fine_total,
        max_overdue_days=max_overdue,
    )


@transaction.atomic
def create_member(data: dict, actor=None, *, create_login: bool = False, password: str | None = None) -> Member:
    member = Member.objects.create(
        roll_number=data["roll_number"],
        name=data["name"],
        department=data["department"],
        academic_year=data["academic_year"],
        email=data["email"],
        phone=data["phone"],
        status=data.get("status", "Active"),
        join_date=data.get("join_date") or timezone.localdate(),
        avatar_url=data.get("avatar_url", ""),
    )
    if create_login:
        from apps.accounts.models import User
        from apps.core.choices import Role

        user = User.objects.create_user(
            username=member.roll_number,
            name=member.name,
            role=Role.STUDENT,
            email=member.email,
            member=member,
        )
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
    return member


@transaction.atomic
def update_member(member: Member, data: dict, actor=None) -> Member:
    old_roll_number = member.roll_number
    for attr in ("roll_number", "name", "department", "academic_year", "email", "phone", "status"):
        if attr in data:
            setattr(member, attr, data[attr])
    member.save()

    if member.roll_number != old_roll_number:
        from apps.accounts.models import User

        User.objects.filter(member=member).update(username=member.roll_number)
    return member


def delete_member(member: Member) -> None:
    try:
        member.delete()
    except ProtectedError as exc:
        raise BusinessRuleError(
            "MEMBER_HAS_HISTORY",
            "This member has loan/fine/booking history and cannot be deleted. Set status to Inactive instead.",
        ) from exc


@transaction.atomic
def block_member(member: Member, reason: str, actor=None) -> Member:
    member.is_blocked = True
    member.block_reason = reason
    member.save(update_fields=["is_blocked", "block_reason", "updated_at"])
    return member


@transaction.atomic
def unblock_member(member: Member, actor=None) -> Member:
    member.is_blocked = False
    member.block_reason = ""
    member.save(update_fields=["is_blocked", "block_reason", "updated_at"])
    return member


@transaction.atomic
def set_block_override(member: Member, reason: str, actor) -> Member:
    member.block_override_by = actor
    member.block_override_by_name = getattr(actor, "name", "") or getattr(actor, "username", "")
    member.block_override_reason = reason
    member.block_override_at = timezone.now()
    member.save(
        update_fields=[
            "block_override_by",
            "block_override_by_name",
            "block_override_reason",
            "block_override_at",
            "updated_at",
        ]
    )
    return member


@transaction.atomic
def clear_block_override(member: Member, actor=None) -> Member:
    member.block_override_by = None
    member.block_override_by_name = ""
    member.block_override_reason = ""
    member.block_override_at = None
    member.save(
        update_fields=[
            "block_override_by",
            "block_override_by_name",
            "block_override_reason",
            "block_override_at",
            "updated_at",
        ]
    )
    return member
