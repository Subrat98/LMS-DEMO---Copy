from django.contrib import admin

from apps.circulation.models import Fine, Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("member", "book_title", "issue_date", "due_date", "return_date", "status")
    search_fields = ("book_title", "copy_barcode", "member__roll_number", "member__name")
    list_filter = ("status",)


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ("member", "book_title", "amount", "status", "created_date")
    list_filter = ("status",)
