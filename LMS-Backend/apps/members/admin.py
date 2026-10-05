from django.contrib import admin

from apps.members.models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("roll_number", "name", "department", "academic_year", "status", "is_blocked")
    search_fields = ("roll_number", "name", "email")
    list_filter = ("department", "academic_year", "status", "is_blocked")
