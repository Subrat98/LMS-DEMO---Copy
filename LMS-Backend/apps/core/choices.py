"""Enum definitions ported 1:1 from the frontend's TypeScript union types.

Values are the literal strings used throughout the old frontend
(`LMS/src/access/permissions.ts`, `LMS/src/types/*.ts`, `LMS/src/constants/departments.ts`)
so JSON payloads read identically on both sides.
"""

from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Administrator"
    LIBRARIAN = "librarian", "Librarian"
    STAFF = "staff", "Staff"
    PRINCIPAL = "principal", "Principal"
    STUDENT = "student", "Student"


STAFF_ROLES = (Role.ADMIN, Role.LIBRARIAN, Role.STAFF, Role.PRINCIPAL)


class UserStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"


class Department(models.TextChoices):
    BA_ODIA = "B.A. Odia", "B.A. Odia"
    BA_ENGLISH = "B.A. English", "B.A. English"
    BA_HISTORY = "B.A. History", "B.A. History"
    BA_POLITICAL_SCIENCE = "B.A. Political Science", "B.A. Political Science"
    BSC_PHYSICS = "B.Sc. Physics", "B.Sc. Physics"
    BSC_CHEMISTRY = "B.Sc. Chemistry", "B.Sc. Chemistry"
    BSC_MATHEMATICS = "B.Sc. Mathematics", "B.Sc. Mathematics"
    BSC_BOTANY = "B.Sc. Botany", "B.Sc. Botany"
    BSC_ZOOLOGY = "B.Sc. Zoology", "B.Sc. Zoology"
    BCOM = "B.Com", "B.Com"


class AcademicYear(models.TextChoices):
    YEAR_1 = "1st Year", "1st Year"
    YEAR_2 = "2nd Year", "2nd Year"
    YEAR_3 = "3rd Year", "3rd Year"


class MemberStatus(models.TextChoices):
    ACTIVE = "Active", "Active"
    INACTIVE = "Inactive", "Inactive"
    SUSPENDED = "Suspended", "Suspended"


class BookCategory(models.TextChoices):
    ARTS = "Arts", "Arts"
    SCIENCE = "Science", "Science"
    COMMERCE = "Commerce", "Commerce"
    LITERATURE = "Literature", "Literature"
    REFERENCE = "Reference", "Reference"


class Classification(models.TextChoices):
    COURSE = "Course", "Course"
    STREAM_ARTS = "Stream - Arts", "Stream - Arts"
    STREAM_SCIENCE = "Stream - Science", "Stream - Science"
    JOURNALS = "Journals", "Journals"
    CURRENT_AFFAIRS = "Current Affairs", "Current Affairs"
    OTHERS = "Others", "Others"


class BookStatus(models.TextChoices):
    AVAILABLE = "Available", "Available"
    FULLY_ISSUED = "Fully Issued", "Fully Issued"
    RETIRED = "Retired", "Retired"


class CopyStatus(models.TextChoices):
    AVAILABLE = "Available", "Available"
    HELD = "Held", "Held"
    ISSUED = "Issued", "Issued"
    LOST = "Lost", "Lost"
    DAMAGED = "Damaged", "Damaged"
    WITHDRAWN = "Withdrawn", "Withdrawn"


MANUAL_COPY_STATUSES = (CopyStatus.AVAILABLE, CopyStatus.LOST, CopyStatus.DAMAGED, CopyStatus.WITHDRAWN)
REASON_REQUIRED_COPY_STATUSES = (CopyStatus.LOST, CopyStatus.DAMAGED, CopyStatus.WITHDRAWN)


class LoanStatus(models.TextChoices):
    ACTIVE = "Active", "Active"
    RETURNED = "Returned", "Returned"


class FineStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    COLLECTED = "Collected", "Collected"
    WAIVED = "Waived", "Waived"


class BookingStatus(models.TextChoices):
    BOOKED = "Booked", "Booked"
    VERIFIED = "Verified", "Verified"
    ISSUED = "Issued", "Issued"
    RETURNED = "Returned", "Returned"
    CANCELLED = "Cancelled", "Cancelled"


OPEN_BOOKING_STATUSES = (BookingStatus.BOOKED, BookingStatus.VERIFIED)


class AuditAction(models.TextChoices):
    CREATE = "Create", "Create"
    UPDATE = "Update", "Update"
    CANCEL = "Cancel", "Cancel"
    VERIFY = "Verify", "Verify"
    ISSUE = "Issue", "Issue"
    RETURN = "Return", "Return"


class ReservationStatus(models.TextChoices):
    WAITING = "Waiting", "Waiting"
    READY = "Ready", "Ready"
    FULFILLED = "Fulfilled", "Fulfilled"
    EXPIRED = "Expired", "Expired"
    CANCELLED = "Cancelled", "Cancelled"


PENDING_RESERVATION_STATUSES = (ReservationStatus.WAITING, ReservationStatus.READY)


class RequestStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    ISSUED = "Issued", "Issued"
    CANCELLED = "Cancelled", "Cancelled"
    EXPIRED = "Expired", "Expired"


OPEN_REQUEST_STATUSES = (RequestStatus.PENDING, RequestStatus.APPROVED)


class NoticeCategory(models.TextChoices):
    ADMISSIONS = "Admissions", "Admissions"
    EXAMINATIONS = "Examinations", "Examinations"
    EVENTS = "Events", "Events"
    CIRCULARS = "Circulars", "Circulars"
    LIBRARY_NOTICES = "Library Notices", "Library Notices"


class PublishStatus(models.TextChoices):
    DRAFT = "Draft", "Draft"
    PUBLISHED = "Published", "Published"


class Stream(models.TextChoices):
    ARTS = "Arts", "Arts"
    SCIENCE = "Science", "Science"
    COMMERCE = "Commerce", "Commerce"
    NONE = "", "General"
