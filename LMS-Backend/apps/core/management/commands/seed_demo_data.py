import random

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.choices import (
    AcademicYear,
    BookCategory,
    Classification,
    Department,
    NoticeCategory,
    Role,
)
from apps.core.dates import add_days, today

# Scaled down from the frontend's SEED_COUNTS (seedConfig.ts) for a fast, deterministic
# standalone seed — proportions are kept similar; raise these if you want a bigger demo.
GENERATED_MEMBERS = 40
GENERATED_BOOKS = 30
OVERDUE_ACTIVE_LOANS = 15
ISSUED_TODAY_LOANS = 8
ON_TIME_ACTIVE_LOANS = 10
RETURNED_LOANS = 60
COLLECTED_FINES = 20
WAIVED_FINES = 5
RESERVATIONS = 8
BOOK_REQUESTS = 6
NOTICES = 10
EBOOKS = 4

FIRST_NAMES = [
    "Ankit", "Priya", "Rahul", "Swagatika", "Debasis", "Manisha", "Suresh", "Ipsita",
    "Bikash", "Rina", "Alok", "Sunita", "Pradeep", "Kavita", "Rajesh", "Sushree",
    "Amit", "Lipsa", "Sanjay", "Nandini",
]
LAST_NAMES = ["Rout", "Patra", "Nayak", "Sahoo", "Behera", "Das", "Mohanty", "Panda", "Pradhan", "Jena"]

SUBJECTS = [
    "Mechanics", "Organic Chemistry", "Calculus", "Modern History", "Political Theory",
    "Microeconomics", "Indian Literature", "Botany Fundamentals", "Zoology", "Accountancy",
]

CLASSIFICATION_BY_CATEGORY = {
    BookCategory.ARTS: Classification.STREAM_ARTS,
    BookCategory.SCIENCE: Classification.STREAM_SCIENCE,
    BookCategory.COMMERCE: Classification.COURSE,
    BookCategory.LITERATURE: Classification.OTHERS,
    BookCategory.REFERENCE: Classification.JOURNALS,
}

WAIVER_REASONS = [
    "Medical emergency — leave documentation on file",
    "First-time offender, goodwill waiver",
    "College event duty exemption",
]


class Command(BaseCommand):
    help = "Seeds a realistic demo dataset so the backend is testable/demoable standalone."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Wipe existing data before seeding.")
        parser.add_argument("--seed", type=int, default=42, help="RNG seed.")

    def handle(self, *args, **options):
        self.rng = random.Random(options["seed"])

        if options["reset"]:
            self._reset()

        with transaction.atomic():
            settings = self._seed_settings()
            users = self._seed_users()
            members = self._seed_members()
            books = self._seed_books()
            self._seed_loans_and_fines(members, books, settings)
            self._seed_holds(members, books)
            self._seed_bookings(members, books)
            self._seed_notices()
            self._seed_ebooks(users)

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write("Demo logins:")
        self.stdout.write("  admin / admin123          (Administrator)")
        self.stdout.write("  librarian / librarian123  (Librarian)")
        self.stdout.write("  librarian2 / librarian123 (Librarian)")
        self.stdout.write("  staff / staff123          (Staff)")
        self.stdout.write("  principal / principal123  (Principal)")
        self.stdout.write("  2026001 / student123      (Student)")

    # -- reset -------------------------------------------------------------

    def _reset(self):
        from apps.bookings.models import Booking, BookingAuditEntry, BookingSequence
        from apps.book_requests.models import BookRequest
        from apps.circulation.models import Fine, Loan
        from apps.catalogue.models import Book, BookCopy
        from apps.ebooks.models import EBook
        from apps.members.models import Member
        from apps.notices.models import Notice
        from apps.reservations.models import Reservation

        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {BookingAuditEntry._meta.db_table}")
        Booking.objects.all().delete()
        BookingSequence.objects.all().delete()
        BookRequest.objects.all().delete()
        Reservation.objects.all().delete()
        Fine.objects.all().delete()
        Loan.objects.all().delete()
        BookCopy.objects.all().delete()
        Book.objects.all().delete()
        Notice.objects.all().delete()
        EBook.objects.all().delete()
        Member.objects.all().delete()

        from apps.accounts.models import User

        User.objects.exclude(is_superuser=True).delete()

    # -- settings / users / members -----------------------------------------

    def _seed_settings(self):
        from apps.library_settings.services import get_settings

        return get_settings()

    def _seed_users(self):
        from apps.accounts.models import User

        demo_accounts = [
            ("admin", "admin123", "Dr. Bijay Mohanty", Role.ADMIN, None),
            ("librarian", "librarian123", "Smita Patra", Role.LIBRARIAN, None),
            ("librarian2", "librarian123", "Manoj Kumar Dash", Role.LIBRARIAN, None),
            ("staff", "staff123", "Priyanka Samal", Role.STAFF, None),
            ("principal", "principal123", "Prof. Ramesh Chandra Jena", Role.PRINCIPAL, None),
        ]
        users = {}
        for username, password, name, role, member in demo_accounts:
            user, _ = User.objects.update_or_create(
                username=username, defaults={"name": name, "role": role}
            )
            user.set_password(password)
            user.save()
            users[username] = user
        return users

    def _seed_members(self):
        from apps.members.models import Member

        members = []
        departments = Department.values
        years = AcademicYear.values

        fixed_student = Member.objects.update_or_create(
            roll_number="2026001",
            defaults={
                "name": "Ankit Rout",
                "department": "B.Sc. Physics",
                "academic_year": "2nd Year",
                "email": "ankit.rout@pscollege.ac.in",
                "phone": "9437100001",
                "status": "Active",
                "join_date": add_days(today(), -400),
            },
        )[0]
        members.append(fixed_student)

        from apps.accounts.models import User

        student_user, _ = User.objects.update_or_create(
            username="2026001", defaults={"name": fixed_student.name, "role": Role.STUDENT, "member": fixed_student}
        )
        student_user.set_password("student123")
        student_user.save()

        # Two fixed "everything cleared" demo members (see LMS frontend's clearance demo data).
        for i, (roll, name, dept) in enumerate(
            [("2026901", "Sushree Jena", "B.Sc. Physics"), ("2026902", "Bikash Panda", "B.A. English")]
        ):
            member, _ = Member.objects.update_or_create(
                roll_number=roll,
                defaults={
                    "name": name,
                    "department": dept,
                    "academic_year": years[i % len(years)],
                    "email": f"{name.split()[0].lower()}@pscollege.ac.in",
                    "phone": f"94371900{i:02d}",
                    "status": "Active",
                    "join_date": add_days(today(), -300),
                },
            )
            members.append(member)

        for i in range(2, GENERATED_MEMBERS):
            first = self.rng.choice(FIRST_NAMES)
            last = self.rng.choice(LAST_NAMES)
            roll = f"2026{i + 2:03d}"
            member, _ = Member.objects.update_or_create(
                roll_number=roll,
                defaults={
                    "name": f"{first} {last}",
                    "department": self.rng.choice(departments),
                    "academic_year": self.rng.choice(years),
                    "email": f"{first.lower()}.{last.lower()}{i}@pscollege.ac.in",
                    "phone": f"94371{self.rng.randint(10000, 99999)}",
                    "status": "Active",
                    "join_date": add_days(today(), -self.rng.randint(30, 700)),
                },
            )
            members.append(member)
        return members

    def _seed_books(self):
        from apps.catalogue import services as catalogue_services

        books = []
        for i in range(GENERATED_BOOKS):
            category = self.rng.choice(BookCategory.values)
            subject = self.rng.choice(SUBJECTS)
            accession = f"PSC-{i + 1:04d}"
            from apps.catalogue.models import Book

            if Book.objects.filter(accession_number=accession).exists():
                books.append(Book.objects.get(accession_number=accession))
                continue
            book = catalogue_services.create_book(
                {
                    "accession_number": accession,
                    "title": f"{subject} — Volume {i + 1}",
                    "author": f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}",
                    "category": category,
                    "classification": CLASSIFICATION_BY_CATEGORY[category],
                    "subject": subject,
                    "price": self.rng.randint(150, 900),
                    "shelf_location": f"R{self.rng.randint(1, 20)}-S{self.rng.randint(1, 8)}",
                    "library_use_only": self.rng.random() < 0.1,
                    "total_copies": self.rng.randint(2, 6),
                }
            )
            books.append(book)
        return books

    # -- loans / fines -------------------------------------------------------

    def _seed_loans_and_fines(self, members, books, settings):
        from apps.circulation import services as circulation_services
        from apps.circulation.models import Fine, Loan
        from apps.circulation.calculators import calculate_due_date, calculate_fine
        from apps.catalogue.models import BookCopy

        borrowable = [b for b in books if not b.library_use_only]
        pool_members = members[3:]  # keep the 2 "cleared demo" members loan-free

        # Active loans: issue "for real" via the service (today-based), then backdate
        # issue/due dates for the overdue subset so they're genuinely overdue as of today.
        active_count = 0
        for _ in range(OVERDUE_ACTIVE_LOANS + ISSUED_TODAY_LOANS + ON_TIME_ACTIVE_LOANS):
            member = self.rng.choice(pool_members)
            book = self.rng.choice(borrowable)
            if Loan.objects.filter(member=member, book=book, status="Active").exists():
                continue
            try:
                loan = circulation_services.issue_book(member=member, book=book, actor=None)
            except Exception:
                continue
            active_count += 1

            if active_count <= OVERDUE_ACTIVE_LOANS:
                overdue_by = self.rng.randint(1, 60)
                issue_date = add_days(today(), -(settings.loan_period_days + overdue_by))
                loan.issue_date = issue_date
                loan.due_date = calculate_due_date(issue_date, settings)
                loan.save(update_fields=["issue_date", "due_date"])
            elif active_count <= OVERDUE_ACTIVE_LOANS + ISSUED_TODAY_LOANS:
                pass  # already issued today by the service
            else:
                issue_date = add_days(today(), -self.rng.randint(1, settings.loan_period_days - 2))
                loan.issue_date = issue_date
                loan.due_date = calculate_due_date(issue_date, settings)
                loan.save(update_fields=["issue_date", "due_date"])

        # Pending fines follow automatically from the overdue active loans above —
        # mirror the frontend's "one pending fine per overdue active loan" rule.
        for loan in Loan.objects.filter(status="Active"):
            from apps.core.dates import overdue_days

            days = overdue_days(loan.due_date)
            if days <= 0:
                continue
            _, amount = calculate_fine(loan.due_date, settings)
            if amount <= 0:
                continue
            Fine.objects.get_or_create(
                loan=loan,
                defaults={
                    "member": loan.member,
                    "member_name": loan.member.name,
                    "book_title": loan.book_title,
                    "overdue_days": days,
                    "amount": amount,
                    "status": "Pending",
                    "created_date": loan.due_date,
                },
            )

        # Returned loans: construct directly with historical dates — the copy nets out
        # to Available (issued-then-returned), so no copy-status service call is needed.
        returned_late_loans = []
        for _ in range(RETURNED_LOANS):
            member = self.rng.choice(pool_members)
            book = self.rng.choice(books)
            copy = BookCopy.objects.filter(book=book, status="Available").order_by("copy_number").first()
            if copy is None:
                continue
            issue_date = add_days(today(), -self.rng.randint(20, 365))
            due_date = calculate_due_date(issue_date, settings)
            return_offset = self.rng.randint(-5, 12)
            return_date = add_days(due_date, return_offset)
            loan = Loan.objects.create(
                member=member,
                book=book,
                copy=copy,
                book_title=book.title,
                accession_number=book.accession_number,
                copy_barcode=copy.barcode,
                issue_date=issue_date,
                due_date=due_date,
                return_date=return_date,
                status="Returned",
            )
            if return_offset > 0:
                returned_late_loans.append(loan)

        self.rng.shuffle(returned_late_loans)
        for loan in returned_late_loans[:COLLECTED_FINES]:
            days = (loan.return_date - loan.due_date).days
            _, amount = calculate_fine(loan.due_date, settings, ref_date=loan.return_date)
            Fine.objects.create(
                loan=loan,
                member=loan.member,
                member_name=loan.member.name,
                book_title=loan.book_title,
                overdue_days=days,
                amount=amount,
                status="Collected",
                created_date=loan.due_date,
                collected_date=loan.return_date,
            )
        for loan in returned_late_loans[COLLECTED_FINES : COLLECTED_FINES + WAIVED_FINES]:
            days = (loan.return_date - loan.due_date).days
            _, amount = calculate_fine(loan.due_date, settings, ref_date=loan.return_date)
            Fine.objects.create(
                loan=loan,
                member=loan.member,
                member_name=loan.member.name,
                book_title=loan.book_title,
                overdue_days=days,
                amount=amount,
                reason=self.rng.choice(WAIVER_REASONS),
                status="Waived",
                created_date=loan.due_date,
                collected_date=loan.return_date,
            )

        # Fixed "fully cleared" demo members: 2 returned-late books each, fine already paid.
        demo_members = [m for m in members if m.roll_number in ("2026901", "2026902")]
        for idx, member in enumerate(demo_members):
            for b in range(2):
                book = borrowable[(idx * 2 + b) % len(borrowable)]
                copy = BookCopy.objects.filter(book=book, status="Available").order_by("copy_number").first()
                if copy is None:
                    continue
                issue_date = add_days(today(), -(60 + idx * 10 + b * 5))
                due_date = calculate_due_date(issue_date, settings)
                return_date = add_days(due_date, 3 + b)
                loan = Loan.objects.create(
                    member=member,
                    book=book,
                    copy=copy,
                    book_title=book.title,
                    accession_number=book.accession_number,
                    copy_barcode=copy.barcode,
                    issue_date=issue_date,
                    due_date=due_date,
                    return_date=return_date,
                    status="Returned",
                )
                days = (return_date - due_date).days
                _, amount = calculate_fine(due_date, settings, ref_date=return_date)
                Fine.objects.create(
                    loan=loan,
                    member=member,
                    member_name=member.name,
                    book_title=loan.book_title,
                    overdue_days=days,
                    amount=amount,
                    status="Collected",
                    created_date=due_date,
                    collected_date=return_date,
                )

    # -- reservations / requests ---------------------------------------------

    def _seed_holds(self, members, books):
        from apps.book_requests import services as request_services
        from apps.reservations import services as reservation_services

        pool_members = members[3:]
        zero_available = [b for b in books if b.available_copies == 0] or books[:3]
        available = [b for b in books if b.available_copies > 0 and not b.library_use_only]

        for _ in range(RESERVATIONS):
            member = self.rng.choice(pool_members)
            book = self.rng.choice(zero_available)
            try:
                reservation_services.reserve(member, book, actor=None)
            except Exception:
                continue

        for i in range(BOOK_REQUESTS):
            if not available:
                break
            member = self.rng.choice(pool_members)
            book = self.rng.choice(available)
            try:
                req = request_services.create_request(member, book, actor=None)
                if i % 2 == 0:
                    request_services.approve_request(req, actor=None)
            except Exception:
                continue

    # -- bookings -------------------------------------------------------------

    def _seed_bookings(self, members, books):
        from apps.bookings import services as booking_services

        pool_members = members[3:]
        available = [b for b in books if b.available_copies > 0 and not b.library_use_only]
        if not available:
            return

        for i in range(10):
            member = self.rng.choice(pool_members)
            book = self.rng.choice(available)
            try:
                booking = booking_services.create_booking(member, book, actor=None)
            except Exception:
                continue
            outcome = i % 5
            try:
                if outcome == 1:
                    booking_services.verify_booking(booking.booking_no, None, actor=None)
                elif outcome == 2:
                    booking_services.issue_booking(booking.booking_no, None, actor=None)
                elif outcome == 3:
                    booking_services.cancel_booking(booking, None, "Seed data: student changed their mind.")
            except Exception:
                continue

    # -- notices / ebooks -----------------------------------------------------

    def _seed_notices(self):
        from apps.notices.models import Notice

        for i in range(NOTICES):
            publish_offset = self.rng.randint(-20, 10)
            has_expiry = self.rng.random() < 0.6
            Notice.objects.get_or_create(
                title=f"Notice #{i + 1}: {self.rng.choice(NoticeCategory.values)} update",
                defaults={
                    "content": "This is a seeded demo notice for the Library Management System.",
                    "category": self.rng.choice(NoticeCategory.values),
                    "publish_date": add_days(today(), publish_offset),
                    "expiry_date": add_days(today(), publish_offset + self.rng.randint(5, 30)) if has_expiry else None,
                    "created_by_name": "Librarian",
                },
            )

    def _seed_ebooks(self, users):
        from apps.ebooks import services as ebook_services

        titles = ["Physics Primer", "Organic Chemistry Notes", "Indian Polity Digest", "Business Accounting Basics"]
        for i, title in enumerate(titles[:EBOOKS]):
            from apps.ebooks.models import EBook

            if EBook.objects.filter(title=title).exists():
                continue
            fake_pdf = SimpleUploadedFile(f"{title.replace(' ', '_')}.pdf", b"%PDF-1.4 seeded placeholder", content_type="application/pdf")
            ebook_services.create_ebook(
                {
                    "title": title,
                    "author": f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}",
                    "classification": self.rng.choice(Classification.values),
                    "file": fake_pdf,
                    "description": "Seeded demo e-book.",
                    "is_published": i % 4 != 3,
                },
                actor=users.get("librarian"),
            )
