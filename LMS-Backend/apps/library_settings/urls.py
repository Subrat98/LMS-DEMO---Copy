from django.urls import path

from apps.library_settings.views import LibrarySettingsView, PublicSettingsView

urlpatterns = [
    path("settings/", LibrarySettingsView.as_view(), name="settings"),
    path("settings/public/", PublicSettingsView.as_view(), name="settings-public"),
]
