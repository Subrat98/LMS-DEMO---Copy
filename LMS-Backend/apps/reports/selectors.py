"""Read-only aggregation queries, replacing the client-side loops in
`LMS/src/utils/circulationStats.ts`, `dashboardStats.ts`, `overdueStats.ts` and
`ReportsPage.tsx`'s inline aggregations.
"""

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from apps.core.choices import BookCategory, FineStatus, LoanStatus
from apps.core.dates import add_days, today


def _add_months(date_value, months: int):
    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    return date_value.replace(year=year, month=month, day=1)


def monthly_circulation(months: int = 6) -> list[dict]:
    from apps.circulation.models import Loan

    end = today().replace(day=1)
    start = _add_months(end, -(months - 1))

    issued_rows = (
        Loan.objects.filter(issue_date__gte=start)
        .annotate(month=TruncMonth("issue_date"))
        .values("month")
        .annotate(issued=Count("id"), renewals=Count("id", filter=Q(renewal_count__gt=0)))
    )
    returned_rows = (
        Loan.objects.filter(return_date__gte=start, status=LoanStatus.RETURNED)
        .annotate(month=TruncMonth("return_date"))
        .values("month")
        .annotate(returned=Count("id"))
    )
    issued_by_month = {row["month"].date(): row for row in issued_rows}
    returned_by_month = {row["month"].date(): row["returned"] for row in returned_rows}

    buckets = []
    cursor = start
    for _ in range(months):
        row = issued_by_month.get(cursor, {})
        buckets.append(
            {
                "month": cursor.strftime("%b %Y"),
                "issued": row.get("issued", 0),
                "returned": returned_by_month.get(cursor, 0),
                "renewals": row.get("renewals", 0),
            }
        )
        cursor = _add_months(cursor, 1)
    return buckets


def category_distribution() -> list[dict]:
    from apps.catalogue.models import Book

    rows = (
        Book.objects.exclude(status="Retired")
        .values("category")
        .annotate(count=Count("id"))
    )
    counts = {row["category"]: row["count"] for row in rows}
    return [{"category": c, "count": counts.get(c, 0)} for c in BookCategory.values]


def holdings_by_category() -> list[dict]:
    from apps.catalogue.models import Book

    rows = (
        Book.objects.exclude(status="Retired")
        .values("category")
        .annotate(titles=Count("id"), total_copies=Sum("total_copies"), available_copies=Sum("available_copies"))
    )
    by_category = {row["category"]: row for row in rows}
    return [
        {
            "category": c,
            "titles": by_category.get(c, {}).get("titles", 0),
            "totalCopies": by_category.get(c, {}).get("total_copies", 0) or 0,
            "availableCopies": by_category.get(c, {}).get("available_copies", 0) or 0,
        }
        for c in BookCategory.values
    ]


def department_usage() -> list[dict]:
    from apps.circulation.models import Loan

    rows = (
        Loan.objects.values("member__department")
        .annotate(loans=Count("id"))
        .order_by("-loans")
    )
    return [{"department": row["member__department"], "loans": row["loans"]} for row in rows]


def overdue_buckets() -> list[dict]:
    from apps.circulation.models import Loan

    ref = today()
    buckets = {"1-7 days": 0, "8-14 days": 0, "15-30 days": 0, "30+ days": 0}
    for loan in Loan.objects.filter(status=LoanStatus.ACTIVE, due_date__lt=ref).only("due_date"):
        days = (ref - loan.due_date).days
        if days <= 7:
            buckets["1-7 days"] += 1
        elif days <= 14:
            buckets["8-14 days"] += 1
        elif days <= 30:
            buckets["15-30 days"] += 1
        else:
            buckets["30+ days"] += 1
    return [{"bucket": k, "count": v} for k, v in buckets.items()]


def overdue_watchlist(limit: int = 5) -> list[dict]:
    from apps.circulation.calculators import calculate_fine
    from apps.circulation.models import Loan
    from apps.core.dates import overdue_days
    from apps.library_settings.services import get_settings

    settings = get_settings()
    loans = (
        Loan.objects.select_related("member")
        .filter(status=LoanStatus.ACTIVE, due_date__lt=today())
        .order_by("due_date")[:limit]
    )
    result = []
    for loan in loans:
        days = overdue_days(loan.due_date)
        _, fine = calculate_fine(loan.due_date, settings)
        result.append(
            {
                "loanId": loan.id,
                "title": loan.book_title,
                "memberName": loan.member.name,
                "rollNumber": loan.member.roll_number,
                "days": days,
                "fine": fine,
            }
        )
    return result


def top_borrowed(days: int = 30, limit: int = 5) -> list[dict]:
    from apps.circulation.models import Loan

    since = add_days(today(), -days)
    rows = (
        Loan.objects.filter(issue_date__gte=since)
        .values("book_id", "book_title")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    return [{"bookId": r["book_id"], "title": r["book_title"], "count": r["count"]} for r in rows]


def fines_breakdown() -> dict:
    from apps.circulation.models import Fine

    totals = Fine.objects.values("status").annotate(amount=Sum("amount"), count=Count("id"))
    by_status = {row["status"]: row for row in totals}

    def _entry(status):
        row = by_status.get(status, {})
        return {"amount": float(row.get("amount") or 0), "count": row.get("count", 0)}

    month_start = today().replace(day=1)
    collected_this_month = (
        Fine.objects.filter(status=FineStatus.COLLECTED, collected_date__gte=month_start).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )
    pending, collected, waived = _entry("Pending"), _entry("Collected"), _entry("Waived")
    return {
        "pending": pending,
        "collected": collected,
        "waived": waived,
        "total": pending["amount"] + collected["amount"] + waived["amount"],
        "collectedThisMonth": float(collected_this_month),
    }


def reservations_by_status() -> dict:
    from apps.reservations.models import Reservation

    return {
        "ready": Reservation.objects.filter(status="Ready").count(),
        "waiting": Reservation.objects.filter(status="Waiting").count(),
    }


def issue_return_summary() -> dict:
    from apps.circulation.models import Loan

    agg = Loan.objects.aggregate(
        issued=Count("id"),
        returned=Count("id", filter=Q(status=LoanStatus.RETURNED)),
        active=Count("id", filter=Q(status=LoanStatus.ACTIVE)),
        renewed=Count("id", filter=Q(renewal_count__gt=0)),
    )
    return agg


def fine_collection(date_from=None, date_to=None) -> dict:
    from apps.circulation.models import Fine

    qs = Fine.objects.filter(status=FineStatus.COLLECTED)
    if date_from:
        qs = qs.filter(collected_date__gte=date_from)
    if date_to:
        qs = qs.filter(collected_date__lte=date_to)
    total = qs.aggregate(total=Sum("amount"))["total"] or 0
    rows = [
        {
            "memberName": f.member_name,
            "bookTitle": f.book_title,
            "amount": float(f.amount),
            "collectedDate": f.collected_date.isoformat() if f.collected_date else None,
        }
        for f in qs.order_by("-collected_date")
    ]
    return {"rows": rows, "total": float(total)}


def fine_register(*, status=None, date_from=None, date_to=None, roll_number=None, department=None, group_by_student=False):
    from apps.circulation.models import Fine

    qs = Fine.objects.select_related("member")
    if status:
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(created_date__gte=date_from)
    if date_to:
        qs = qs.filter(created_date__lte=date_to)
    if roll_number:
        qs = qs.filter(member__roll_number=roll_number)
    if department:
        qs = qs.filter(member__department=department)

    if not group_by_student:
        return [
            {
                "id": f.id,
                "rollNumber": f.member.roll_number,
                "memberName": f.member_name,
                "bookTitle": f.book_title,
                "overdueDays": f.overdue_days,
                "amount": float(f.amount),
                "status": f.status,
                "createdDate": f.created_date.isoformat(),
                "collectedDate": f.collected_date.isoformat() if f.collected_date else None,
            }
            for f in qs.order_by("-created_date")
        ]

    rows = qs.values("member__roll_number", "member_name").annotate(count=Count("id"), amount=Sum("amount"))
    return [
        {"rollNumber": r["member__roll_number"], "name": r["member_name"], "count": r["count"], "amount": float(r["amount"])}
        for r in rows
    ]


def dashboard_summary() -> dict:
    from apps.circulation.models import Fine, Loan
    from apps.core.dashboard_totals import DASHBOARD_TOTALS
    from apps.members.models import Member
    from apps.notices.models import Notice

    ref = today()
    active_members = Member.objects.filter(status="Active").count()
    issued_today = Loan.objects.filter(issue_date=ref).count()
    due_today = Loan.objects.filter(status=LoanStatus.ACTIVE, due_date=ref).count()
    returned_today = Loan.objects.filter(return_date=ref).count()
    overdue_count = Loan.objects.filter(status=LoanStatus.ACTIVE, due_date__lt=ref).count()
    pending_fine_total = (
        Fine.objects.filter(status=FineStatus.PENDING).aggregate(total=Sum("amount"))["total"] or 0
    )

    return {
        "totals": DASHBOARD_TOTALS,
        "activeMembers": active_members,
        "issuedToday": issued_today,
        "dueToday": due_today,
        "returnedToday": returned_today,
        "overdueCount": overdue_count,
        "pendingFineTotal": float(pending_fine_total),
        "reservationsByStatus": reservations_by_status(),
        "topBorrowed": top_borrowed(),
        "monthlyCirculation": monthly_circulation(6),
        "categoryDistribution": category_distribution(),
        "overdueSummary": overdue_buckets(),
        "overdueWatchlist": overdue_watchlist(),
        "finesBreakdown": fines_breakdown(),
        "latestNotices": list(
            Notice.objects.filter(publish_date__lte=ref)
            .exclude(expiry_date__lt=ref)
            .order_by("-publish_date")
            .values("id", "title", "category", "publish_date")[:4]
        ),
    }
