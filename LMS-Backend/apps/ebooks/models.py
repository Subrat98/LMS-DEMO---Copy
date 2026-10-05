from django.db import models

from apps.core.choices import Classification, PublishStatus
from apps.ebooks.validators import validate_ebook_file


class EBook(models.Model):
    title = models.CharField(max_length=300)
    author = models.CharField(max_length=200)
    classification = models.CharField(max_length=20, choices=Classification.choices)

    file = models.FileField(upload_to="ebooks/%Y/%m/", validators=[validate_ebook_file])
    file_size_bytes = models.PositiveIntegerField(default=0)

    publish_status = models.CharField(max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT)
    description = models.TextField(blank=True)

    uploaded_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    uploaded_by_name = models.CharField(max_length=150, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    download_count = models.PositiveIntegerField(default=0)
    syllabus = models.JSONField(null=True, blank=True)

    stream = models.CharField(max_length=10, blank=True, db_index=True)
    syllabus_streams = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        from apps.core.stream import stream_of_item, syllabus_streams_string

        self.stream = stream_of_item(None, self.classification)
        self.syllabus_streams = syllabus_streams_string(self.syllabus)
        super().save(*args, **kwargs)
