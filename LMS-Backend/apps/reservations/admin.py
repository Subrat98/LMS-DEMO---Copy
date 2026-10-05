from django.contrib import admin

from apps.reservations.models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("member", "book_title", "queue_position", "status", "reserved_date")
    list_filter = ("status",)
