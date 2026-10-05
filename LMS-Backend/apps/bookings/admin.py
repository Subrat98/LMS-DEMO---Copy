from django.contrib import admin

from apps.bookings.models import Booking, BookingAuditEntry, BookingSequence


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("booking_no", "member", "book_title", "status", "booking_date", "expiry_date")
    search_fields = ("booking_no", "student_name", "book_title")
    list_filter = ("status",)


@admin.register(BookingAuditEntry)
class BookingAuditEntryAdmin(admin.ModelAdmin):
    list_display = ("booking_no", "action", "user_name", "action_time")
    search_fields = ("booking_no", "user_name")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(BookingSequence)
