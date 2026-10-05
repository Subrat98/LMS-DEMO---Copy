from django.contrib import admin

from apps.library_settings.models import LibrarySettings


@admin.register(LibrarySettings)
class LibrarySettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "loan_period_days", "fine_per_day", "updated_at")
