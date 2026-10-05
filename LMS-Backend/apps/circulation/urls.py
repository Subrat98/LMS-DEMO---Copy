from rest_framework.routers import DefaultRouter

from apps.circulation.views import FineViewSet, LoanViewSet

router = DefaultRouter()
router.register("loans", LoanViewSet, basename="loan")
router.register("fines", FineViewSet, basename="fine")

urlpatterns = router.urls
