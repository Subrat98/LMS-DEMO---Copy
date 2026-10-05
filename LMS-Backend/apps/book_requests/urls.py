from rest_framework.routers import DefaultRouter

from apps.book_requests.views import BookRequestViewSet

router = DefaultRouter()
router.register("book-requests", BookRequestViewSet, basename="book-request")

urlpatterns = router.urls
