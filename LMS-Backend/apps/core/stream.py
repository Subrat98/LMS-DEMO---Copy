"""Stream/syllabus visibility ported from `LMS/src/utils/stream.ts`.

Governs which books/e-books a student may see, request, book or reserve, based on their
department. This filtering must be applied server-side (the frontend only ever applied it
client-side, which let a student query the raw list and see out-of-stream titles).
"""

from django.db.models import Q

from apps.core.choices import BookCategory, Classification, Stream

_PREFIX_MAP = (
    ("b.a", Stream.ARTS),
    ("ba.", Stream.ARTS),
    ("b.sc", Stream.SCIENCE),
    ("bsc", Stream.SCIENCE),
    ("b.com", Stream.COMMERCE),
    ("bcom", Stream.COMMERCE),
)

_CATEGORY_STREAM = {
    BookCategory.ARTS: Stream.ARTS,
    BookCategory.LITERATURE: Stream.ARTS,
    BookCategory.SCIENCE: Stream.SCIENCE,
    BookCategory.COMMERCE: Stream.COMMERCE,
}

_CLASSIFICATION_STREAM = {
    Classification.STREAM_ARTS: Stream.ARTS,
    Classification.STREAM_SCIENCE: Stream.SCIENCE,
}


def stream_of_programme(programme: str | None) -> str | None:
    """None means "unrecognized department" -> sees everything (matches the frontend)."""
    if not programme:
        return None
    normalized = programme.strip().lower()
    for prefix, stream in _PREFIX_MAP:
        if normalized.startswith(prefix):
            return stream.value
    return None


def stream_of_member(member) -> str | None:
    return stream_of_programme(member.department)


def stream_of_item(category: str | None, classification: str | None) -> str:
    """Returns '' (general/visible-to-all) when neither classification nor category resolves."""
    if classification in _CLASSIFICATION_STREAM:
        return _CLASSIFICATION_STREAM[classification].value
    if category in _CATEGORY_STREAM:
        return _CATEGORY_STREAM[category].value
    return ""


def syllabus_streams_string(syllabus: list[dict] | None) -> str:
    """Builds the denormalized ',Arts,Science,' style string stored on Book/EBook."""
    if not syllabus:
        return ""
    streams = {stream_of_programme(tag.get("programme")) for tag in syllabus}
    streams.discard(None)
    if not streams:
        return ""
    return "," + ",".join(sorted(streams)) + ","


def is_on_syllabus(syllabus: list[dict] | None, member) -> bool:
    if not syllabus:
        return False
    return any(
        tag.get("programme") == member.department and tag.get("year") == member.academic_year
        for tag in syllabus
    )


def is_visible_to_member(item, member) -> bool:
    """Single-item equivalent of `visible_q`, for a one-off check (e.g. before a booking).

    `item` must have `.category`, `.classification` and `.syllabus` (Book/EBook-shaped).
    """
    member_stream = stream_of_member(member)
    if member_stream is None:
        return True
    item_stream = stream_of_item(getattr(item, "category", None), getattr(item, "classification", None))
    if item_stream in ("", member_stream):
        return True
    return is_on_syllabus(item.syllabus, member)


def visible_q(stream: str | None, *, stream_field: str = "stream", syllabus_field: str = "syllabus_streams") -> Q:
    """Queryset filter: a `None` stream (unrecognized department) sees everything."""
    if stream is None:
        return Q()
    return (
        Q(**{stream_field: ""})
        | Q(**{stream_field: stream})
        | Q(**{f"{syllabus_field}__contains": f",{stream},"})
    )
