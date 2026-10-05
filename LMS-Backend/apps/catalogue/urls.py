from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.catalogue.views import BookViewSet, CopyDetailView, CopyStatusView

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")

urlpatterns = [
    path("copies/<str:barcode>/", CopyDetailView.as_view(), name="copy-detail"),
    path("copies/<str:barcode>/status/", CopyStatusView.as_view(), name="copy-status"),
] + router.urls
