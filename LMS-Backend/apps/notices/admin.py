from django.contrib import admin

from apps.notices.models import Notice


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "publish_date", "expiry_date")
    list_filter = ("category",)
    search_fields = ("title", "content")
