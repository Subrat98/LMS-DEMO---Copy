from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

api_urls = [
    path("", include("apps.accounts.urls")),
    path("", include("apps.library_settings.urls")),
    path("", include("apps.catalogue.urls")),
    path("", include("apps.members.urls")),
    path("", include("apps.reservations.urls")),
    path("", include("apps.book_requests.urls")),
    path("", include("apps.circulation.urls")),
    path("", include("apps.bookings.urls")),
    path("", include("apps.notices.urls")),
    path("", include("apps.ebooks.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.student.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
