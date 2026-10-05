from django.contrib import admin

from apps.catalogue.models import Book, BookCopy


class BookCopyInline(admin.TabularInline):
    model = BookCopy
    extra = 0
    readonly_fields = ("barcode", "copy_number")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("accession_number", "title", "author", "category", "status", "available_copies", "total_copies")
    search_fields = ("accession_number", "title", "author", "isbn")
    list_filter = ("category", "classification", "status", "library_use_only")
    inlines = [BookCopyInline]


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ("barcode", "book", "copy_number", "status")
    search_fields = ("barcode",)
    list_filter = ("status",)
