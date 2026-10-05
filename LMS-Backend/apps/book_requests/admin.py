from django.contrib import admin

from apps.book_requests.models import BookRequest


@admin.register(BookRequest)
class BookRequestAdmin(admin.ModelAdmin):
    list_display = ("member", "book_title", "status", "requested_date")
    list_filter = ("status",)
