from django.db import models

from apps.core.choices import NoticeCategory


class Notice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=NoticeCategory.choices)
    publish_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_by_name = models.CharField(max_length=150, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-publish_date"]

    def __str__(self):
        return self.title
