from django.contrib import admin

from apps.ebooks.models import EBook


@admin.register(EBook)
class EBookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "classification", "publish_status", "download_count")
    list_filter = ("classification", "publish_status")
    search_fields = ("title", "author")
