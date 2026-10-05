from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.choices import Role, UserStatus


class User(AbstractUser):
    """Custom user: `first_name`/`last_name` are dropped in favour of a single `name` field.

    A student's `username` is their roll number, and `member` links to their `Member` row
    (this replaces the frontend's `User.memberId`).
    """

    first_name = None
    last_name = None

    name = models.CharField(max_length=150)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.STUDENT)
    status = models.CharField(max_length=12, choices=UserStatus.choices, default=UserStatus.ACTIVE)
    phone = models.CharField(max_length=15, blank=True)
    avatar_url = models.URLField(blank=True)
    member = models.OneToOneField(
        "members.Member", null=True, blank=True, on_delete=models.SET_NULL, related_name="user"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role="student") | models.Q(member__isnull=True),
                name="member_link_only_for_students",
            )
        ]

    def save(self, *args, **kwargs):
        self.is_active = self.status == UserStatus.ACTIVE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
