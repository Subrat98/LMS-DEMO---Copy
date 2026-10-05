from rest_framework.routers import DefaultRouter

from apps.bookings.views import BookingAuditViewSet, BookingViewSet

router = DefaultRouter()
router.register("bookings", BookingViewSet, basename="booking")
router.register("booking-audit", BookingAuditViewSet, basename="booking-audit")

urlpatterns = router.urls
