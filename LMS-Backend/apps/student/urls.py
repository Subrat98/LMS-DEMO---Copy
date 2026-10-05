from django.urls import path

from apps.student import views

urlpatterns = [
    path("student/me/", views.MeView.as_view(), name="student-me"),
    path("student/dashboard/", views.DashboardView.as_view(), name="student-dashboard"),
    path("student/catalogue/", views.CatalogueView.as_view(), name="student-catalogue"),
    path("student/catalogue/<int:pk>/", views.CatalogueDetailView.as_view(), name="student-catalogue-detail"),
    path("student/loans/", views.LoanListView.as_view(), name="student-loans"),
    path("student/loans/<int:pk>/renew/", views.LoanRenewView.as_view(), name="student-loan-renew"),
    path("student/fines/", views.FineListView.as_view(), name="student-fines"),
    path("student/bookings/", views.BookingListCreateView.as_view(), name="student-bookings"),
    path("student/bookings/<str:booking_no>/", views.BookingDetailView.as_view(), name="student-booking-detail"),
    path(
        "student/bookings/<str:booking_no>/cancel/",
        views.BookingCancelView.as_view(),
        name="student-booking-cancel",
    ),
    path("student/book-requests/", views.BookRequestListCreateView.as_view(), name="student-book-requests"),
    path(
        "student/book-requests/<int:pk>/cancel/",
        views.BookRequestCancelView.as_view(),
        name="student-book-request-cancel",
    ),
    path("student/reservations/", views.ReservationListCreateView.as_view(), name="student-reservations"),
    path(
        "student/reservations/<int:pk>/cancel/",
        views.ReservationCancelView.as_view(),
        name="student-reservation-cancel",
    ),
    path("student/ebooks/", views.EBookListView.as_view(), name="student-ebooks"),
    path("student/ebooks/<int:pk>/open/", views.EBookOpenView.as_view(), name="student-ebook-open"),
    path("student/ebooks/<int:pk>/file/", views.EBookFileView.as_view(), name="student-ebook-file"),
    path("student/notices/", views.NoticeListView.as_view(), name="student-notices"),
    path("student/clearance/", views.ClearanceView.as_view(), name="student-clearance"),
]
