from django.db import models

from apps.core.choices import BookCategory, BookStatus, Classification, CopyStatus


class Book(models.Model):
    accession_number = models.CharField(max_length=30, unique=True)
    title = models.CharField(max_length=300, db_index=True)
    author = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=BookCategory.choices, db_index=True)
    classification = models.CharField(max_length=20, choices=Classification.choices, db_index=True)
    subject = models.CharField(max_length=150, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    isbn = models.CharField(max_length=20, blank=True)
    publisher = models.CharField(max_length=150, blank=True)
    edition = models.CharField(max_length=50, blank=True)

    # Written only by catalogue.services._sync_book_counts — never set directly elsewhere.
    total_copies = models.PositiveIntegerField(default=0)
    available_copies = models.PositiveIntegerField(default=0)

    shelf_location = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=BookStatus.choices, default=BookStatus.AVAILABLE, db_index=True)
    library_use_only = models.BooleanField(default=False)

    cover_image = models.URLField(blank=True)
    acquisition_date = models.DateField(null=True, blank=True)
    acquisition_source = models.CharField(max_length=150, blank=True)
    added_date = models.DateField(auto_now_add=True)

    syllabus = models.JSONField(null=True, blank=True)

    # Denormalized visibility fields, recomputed in save() — see apps.core.stream.
    stream = models.CharField(max_length=10, blank=True, db_index=True)
    syllabus_streams = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.accession_number} — {self.title}"

    def save(self, *args, **kwargs):
        from apps.core.stream import stream_of_item, syllabus_streams_string

        self.stream = stream_of_item(self.category, self.classification)
        self.syllabus_streams = syllabus_streams_string(self.syllabus)
        super().save(*args, **kwargs)


class BookCopy(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")
    copy_number = models.PositiveSmallIntegerField()
    barcode = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20, choices=CopyStatus.choices, default=CopyStatus.AVAILABLE, db_index=True)
    status_reason = models.CharField(max_length=300, blank=True)
    status_changed_date = models.DateField(null=True, blank=True)
    shelf_location = models.CharField(max_length=50, blank=True)
    added_date = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["book", "copy_number"], name="unique_copy_number_per_book")]
        indexes = [models.Index(fields=["book", "status", "copy_number"])]
        ordering = ["book", "copy_number"]

    def __str__(self):
        return self.barcode
