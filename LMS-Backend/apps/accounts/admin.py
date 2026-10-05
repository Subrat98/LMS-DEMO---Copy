from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("name", "email", "phone", "avatar_url", "member")}),
        ("Role & status", {"fields": ("role", "status", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    list_display = ("username", "name", "role", "status", "is_staff")
    search_fields = ("username", "name", "email")
