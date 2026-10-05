from django.db.models import Q
from django.http import FileResponse
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from apps.accounts.serializers import UserSerializer
from apps.bookings import services as booking_services
from apps.bookings.models import Booking
from apps.bookings.serializers import BookingSerializer, BookingUpdateSerializer
from apps.book_requests import services as request_services
from apps.book_requests.models import BookRequest
from apps.book_requests.serializers import BookRequestSerializer
from apps.catalogue.models import Book
from apps.circulation import services as circulation_services
from apps.circulation.models import Fine, Loan
from apps.circulation.serializers import FineSerializer, LoanSerializer
from apps.core.choices import LoanStatus, OPEN_BOOKING_STATUSES, OPEN_REQUEST_STATUSES, PublishStatus
from apps.core.dates import add_days, today
from apps.core.stream import stream_of_member, visible_q
from apps.core.views import BaseStudentView
from apps.ebooks import services as ebook_services
from apps.ebooks.models import EBook
from apps.ebooks.serializers import EBookSerializer
from apps.library_settings.services import get_settings
from apps.notices.models import Notice
from apps.notices.serializers import NoticeSerializer
from apps.reservations import services as reservation_services
from apps.reservations.models import Reservation
from apps.reservations.serializers import ReservationSerializer
from apps.reports.clearance import compute_clearance
from apps.student.serializers import StudentBookSerializer


class MeView(BaseStudentView):
    def get(self, request):
        member = self.member
        settings = get_settings()
        active_loans = Loan.objects.filter(member=member, status=LoanStatus.ACTIVE).count()
        open_bookings = Booking.objects.filter(member=member, status__in=OPEN_BOOKING_STATUSES).count()
        return Response(
            {
                "user": UserSerializer(request.user).data,
                "activeLoans": active_loans,
                "openBookings": open_bookings,
                "maxConcurrentLoans": settings.max_concurrent_loans,
                "slotsLeft": max(0, settings.max_concurrent_loans - active_loans - open_bookings),
            }
        )


class DashboardView(BaseStudentView):
    def get(self, request):
        member = self.member
        settings = get_settings()
        due_soon_cutoff = add_days(today(), settings.due_reminder_lead_days)
        due_soon = Loan.objects.filter(member=member, status=LoanStatus.ACTIVE, due_date__lte=due_soon_cutoff)
        pending_fine_total = sum(
            float(f.amount) for f in Fine.objects.filter(member=member, status="Pending")
        )
        open_holds = (
            Booking.objects.filter(member=member, status__in=OPEN_BOOKING_STATUSES).count()
            + BookRequest.objects.filter(member=member, status__in=OPEN_REQUEST_STATUSES).count()
            + Reservation.objects.filter(member=member, status__in=("Waiting", "Ready")).count()
        )
        ref = today()
        notices = Notice.objects.filter(publish_date__lte=ref).exclude(expiry_date__lt=ref).order_by("-publish_date")[:4]
        return Response(
            {
                "dueSoonLoans": LoanSerializer(due_soon, many=True).data,
                "pendingFineTotal": pending_fine_total,
                "openHolds": open_holds,
                "notices": NoticeSerializer(notices, many=True).data,
            }
        )


class CatalogueView(BaseStudentView):
    def get(self, request):
        member = self.member
        stream = stream_of_member(member)
        qs = Book.objects.exclude(status="Retired").filter(visible_q(stream))

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(author__icontains=search))
        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        if request.query_params.get("available") == "true":
            qs = qs.filter(available_copies__gt=0)

        serializer = StudentBookSerializer(qs, many=True, context={"member": member})
        data = serializer.data
        if request.query_params.get("onSyllabus") == "true":
            data = [row for row in data if row["is_on_syllabus"]]
        return Response(data)


class CatalogueDetailView(BaseStudentView):
    def get(self, request, pk):
        member = self.member
        stream = stream_of_member(member)
        book = get_object_or_404(Book.objects.filter(visible_q(stream)), pk=pk)
        return Response(StudentBookSerializer(book, context={"member": member}).data)


class LoanListView(BaseStudentView):
    def get(self, request):
        qs = Loan.objects.filter(member=self.member)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(LoanSerializer(qs.order_by("-issue_date"), many=True).data)


class LoanRenewView(BaseStudentView):
    def post(self, request, pk):
        loan = get_object_or_404(Loan, pk=pk, member=self.member)
        loan = circulation_services.renew_loan(loan, actor=request.user)
        return Response(LoanSerializer(loan).data)


class FineListView(BaseStudentView):
    def get(self, request):
        qs = Fine.objects.filter(member=self.member).order_by("-created_date")
        return Response(FineSerializer(qs, many=True).data)


class BookingListCreateView(BaseStudentView):
    def get(self, request):
        qs = Booking.objects.filter(member=self.member).order_by("-booking_date")
        return Response(BookingSerializer(qs, many=True).data)

    def post(self, request):
        accession_number = request.data.get("accessionNumber") or request.data.get("accession_number")
        book = get_object_or_404(Book, accession_number__iexact=accession_number)
        booking = booking_services.create_booking(self.member, book, actor=request.user)
        return Response(BookingSerializer(booking).data, status=201)


class BookingDetailView(BaseStudentView):
    def patch(self, request, booking_no):
        booking = get_object_or_404(Booking, booking_no=booking_no, member=self.member)
        serializer = BookingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.update_booking(booking, serializer.validated_data["accession_number"], request.user)
        return Response(BookingSerializer(booking).data)


class BookingCancelView(BaseStudentView):
    def post(self, request, booking_no):
        booking = get_object_or_404(Booking, booking_no=booking_no, member=self.member)
        booking = booking_services.cancel_booking(booking, request.user, request.data.get("reason", ""))
        return Response(BookingSerializer(booking).data)


class BookRequestListCreateView(BaseStudentView):
    def get(self, request):
        qs = BookRequest.objects.filter(member=self.member).order_by("-requested_date")
        return Response(BookRequestSerializer(qs, many=True).data)

    def post(self, request):
        accession_number = request.data.get("accessionNumber") or request.data.get("accession_number")
        book = get_object_or_404(Book, accession_number__iexact=accession_number)
        req = request_services.create_request(self.member, book, actor=request.user)
        return Response(BookRequestSerializer(req).data, status=201)


class BookRequestCancelView(BaseStudentView):
    def post(self, request, pk):
        req = get_object_or_404(BookRequest, pk=pk, member=self.member)
        req = request_services.cancel_request(req, actor=request.user)
        return Response(BookRequestSerializer(req).data)


class ReservationListCreateView(BaseStudentView):
    def get(self, request):
        qs = Reservation.objects.filter(member=self.member).order_by("-reserved_date")
        return Response(ReservationSerializer(qs, many=True).data)

    def post(self, request):
        accession_number = request.data.get("accessionNumber") or request.data.get("accession_number")
        book = get_object_or_404(Book, accession_number__iexact=accession_number)
        reservation = reservation_services.reserve(self.member, book, actor=request.user)
        return Response(ReservationSerializer(reservation).data, status=201)


class ReservationCancelView(BaseStudentView):
    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk, member=self.member)
        reservation = reservation_services.cancel_reservation(reservation, actor=request.user)
        return Response(ReservationSerializer(reservation).data)


class EBookListView(BaseStudentView):
    def get(self, request):
        member = self.member
        stream = stream_of_member(member)
        qs = EBook.objects.filter(publish_status=PublishStatus.PUBLISHED).filter(visible_q(stream))
        return Response(EBookSerializer(qs, many=True, context={"request": request}).data)


class EBookOpenView(BaseStudentView):
    def post(self, request, pk):
        member = self.member
        stream = stream_of_member(member)
        ebook = get_object_or_404(
            EBook.objects.filter(publish_status=PublishStatus.PUBLISHED).filter(visible_q(stream)), pk=pk
        )
        ebook_services.increment_download(ebook)
        return Response({"fileUrl": EBookSerializer(ebook, context={"request": request}).data["file_url"]})


class EBookFileView(BaseStudentView):
    def get(self, request, pk):
        member = self.member
        stream = stream_of_member(member)
        ebook = get_object_or_404(
            EBook.objects.filter(publish_status=PublishStatus.PUBLISHED).filter(visible_q(stream)), pk=pk
        )
        return FileResponse(ebook.file.open("rb"), filename=ebook.file.name.split("/")[-1])


class NoticeListView(BaseStudentView):
    def get(self, request):
        ref = today()
        qs = Notice.objects.filter(publish_date__lte=ref).exclude(expiry_date__lt=ref).order_by("-publish_date")
        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return Response(NoticeSerializer(qs, many=True).data)


class ClearanceView(BaseStudentView):
    def get(self, request):
        return Response(compute_clearance(self.member))
