from rest_framework.routers import DefaultRouter

from apps.reservations.views import ReservationViewSet

router = DefaultRouter()
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = router.urls
