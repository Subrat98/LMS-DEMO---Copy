from rest_framework.routers import DefaultRouter

from apps.ebooks.views import EBookViewSet

router = DefaultRouter()
router.register("ebooks", EBookViewSet, basename="ebook")

urlpatterns = router.urls
