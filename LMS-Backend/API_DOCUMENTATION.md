# PSC College LMS — API Documentation

A Django REST Framework backend for the Library Management System, replacing the old
frontend-only (localStorage) prototype with a real, server-enforced API.

- **Base URL:** `http://localhost:8000/api/v1`
- **Interactive docs:** `http://localhost:8000/api/docs` (Swagger UI), `/api/redoc` (ReDoc), `/api/schema` (raw OpenAPI)
- **Format:** JSON, **camelCase** on the wire (models are snake_case internally; a middleware converts both ways)
- **Dates:** `YYYY-MM-DD` (date-only fields: issue/due/return/booking/expiry/publish/join dates)
- **Timestamps:** ISO 8601 with offset, e.g. `2026-10-05T20:50:12.534951+05:30` (`Asia/Kolkata`)
- **Money:** plain JSON numbers (INR), e.g. `12.5`, not strings

---

## 1. Authentication

JWT via `djangorestframework-simplejwt`. Send the access token as:

```
Authorization: Bearer <access_token>
```

| Token | Lifetime |
|---|---|
| Access | 30 minutes |
| Refresh | 7 days (rotates on use; the old refresh token is blacklisted) |

### `POST /auth/login/`

**Request**
```json
{ "username": "librarian", "password": "librarian123" }
```

**Response `200`**
```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "user": {
    "id": 2, "username": "librarian", "name": "Smita Patra", "role": "librarian",
    "status": "active", "email": "", "phone": "", "avatarUrl": "",
    "rollNumber": null, "createdAt": "2026-10-05T20:50:12+05:30", "lastLoginAt": null
  }
}
```
A student logs in with their **roll number** as `username` (e.g. `2026001`), not a separate ID — see §3.

**Errors:** `400` with `code: "ACCOUNT_SUSPENDED"` (suspended account), `401` generic bad credentials.

### `POST /auth/refresh/`
**Request:** `{ "refresh": "<jwt>" }` → **Response:** `{ "access": "<jwt>", "refresh": "<jwt>" }`

### `POST /auth/logout/` *(auth required)*
**Request:** `{ "refresh": "<jwt>" }` → blacklists it. **Response:** `204`.

### `GET /auth/me/` / `PATCH /auth/me/` *(auth required)*
PATCH body: any of `{ "name", "email", "phone", "avatarUrl" }`.

### `POST /auth/change-password/` *(auth required)*
```json
{ "currentPassword": "old", "newPassword": "new-password" }
```
On success (`204`), all of that user's outstanding refresh tokens are blacklisted.

### Demo accounts (seeded by `seed_demo_data`)

| Username | Password | Role |
|---|---|---|
| admin | admin123 | Administrator |
| librarian | librarian123 | Librarian |
| librarian2 | librarian123 | Librarian |
| staff | staff123 | Staff |
| principal | principal123 | Principal |
| 2026001 | student123 | Student (roll number `2026001`) |

---

## 2. Conventions

### Pagination
List endpoints return:
```json
{ "count": 30, "next": "http://.../?page=2&pageSize=25", "previous": null, "results": [ ... ] }
```
`?page=` and `?pageSize=` (default 25, max 200) control paging.

### Filtering / search / ordering
Most list endpoints accept `?search=`, model-specific filters (documented per endpoint below), and `?ordering=field` / `?ordering=-field`.

### Errors
Every error response has the same envelope:
```json
{ "error": { "code": "LOAN_LIMIT_REACHED", "message": "This member already has the maximum of 2 book(s) issued.", "fields": {} } }
```
- `fields` is present only for `400 VALIDATION_ERROR` (serializer field errors).
- Business-rule violations are always `400` with a specific `code` (see the appendix in §13).
- `401 NOT_AUTHENTICATED`, `403 PERMISSION_DENIED`, `404 NOT_FOUND` follow the same envelope.

### The roll number *is* the member ID
There is **no separate `memberId`** (the old frontend's `MEM-1001` scheme is gone). A member's
`rollNumber` is their one business identifier everywhere:
- URL lookups: `GET /members/{rollNumber}/`
- Every cross-reference (`Loan.rollNumber`, `Fine.rollNumber`, `Booking.rollNumber`, etc.) is a roll number.
- A student's login `username` **is** their roll number.

---

## 3. Permission matrix

Enforced server-side on every request (`request.user.role`, read fresh from the database —
never trusted from the JWT). Students have no matrix entries; they only ever use `/student/*`
endpoints, scoped to their own `Member` record.

| Module | admin | librarian | staff | principal |
|---|---|---|---|---|
| books | view,create,edit,delete | view,create,edit,delete | view | view |
| circulation | view,create,edit | view,create,edit | view,create,edit | — |
| members | view,create,edit,delete | view,create,edit | — | — |
| reservations | view,create,edit | view,create,edit | view,create,edit | — |
| fines | view,edit | view,edit | view | view |
| reports | view | view | — | view |
| librarySettings | view,edit | — | — | — |
| notices | view,create,edit,delete | view,create,edit,delete | view | view |
| bookings | view,edit | view,edit,create | — | view,edit |
| bookingAudit | view | view | — | view |

`/users/` (account management) is admin-only and outside this matrix.

---

## 4. Books & Copies (`books` module)

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET | `/books/` | books.view | `?search=&category=&classification=&status=&libraryUseOnly=&available=true&accessionNumber=` |
| POST | `/books/` | books.create | creates the Book **and** its copies |
| GET | `/books/{id}/` | books.view | includes `copies[]` |
| PUT/PATCH | `/books/{id}/` | books.edit | changing `totalCopies` adds/removes copies |
| DELETE | `/books/{id}/` | books.delete | `400 BOOK_HAS_HISTORY` if loans/bookings reference it — retire instead |
| POST | `/books/{id}/retire/` | books.edit | |
| POST | `/books/{id}/reinstate/` | books.edit | |
| POST | `/books/bulk-import/` | books.create | multipart CSV, see below |
| GET | `/books/bulk-import/template/` | books.create | downloads the CSV header row |
| GET/POST | `/books/{id}/copies/` | books.view / books.edit | POST body `{ "count": 3 }` |
| GET | `/copies/{barcode}/` | books.view | includes `heldFor` (booking/request/reservation) or `null` |
| PATCH | `/copies/{barcode}/status/` | books.edit | `{ "status": "Lost", "reason": "..." }` |

**Create book — request**
```json
{
  "accessionNumber": "PSC-0099", "title": "Quantum Mechanics", "author": "J. Smith",
  "category": "Science", "classification": "Stream - Science", "subject": "Physics",
  "totalCopies": 3, "shelfLocation": "R2-S4", "libraryUseOnly": false
}
```
**Response `201`**
```json
{
  "id": 61, "accessionNumber": "PSC-0099", "title": "Quantum Mechanics", "author": "J. Smith",
  "category": "Science", "classification": "Stream - Science", "subject": "Physics",
  "price": "0.00", "isbn": "", "publisher": "", "edition": "",
  "totalCopies": 3, "availableCopies": 3, "shelfLocation": "R2-S4",
  "status": "Available", "libraryUseOnly": false, "coverImage": "", "acquisitionDate": null,
  "acquisitionSource": "", "addedDate": "2026-10-05", "syllabus": null,
  "copies": [
    { "id": 301, "barcode": "PSC-0099-01", "accessionNumber": "PSC-0099", "book": 61, "copyNumber": 1, "status": "Available", "statusReason": "", "statusChangedDate": null, "shelfLocation": "", "addedDate": "2026-10-05", "heldFor": null }
  ]
}
```

**Bulk import CSV columns** (positional, no header-name matching):
`AccessionNumber, Title, Author, Subject, Classification, Publisher, Edition, ISBN, Price, Copies, ShelfLocation, LibraryUseOnly`

**Response**
```json
{ "imported": 18, "failed": 2, "errors": [ { "rowNumber": 5, "data": ["", "No Title", ...], "reason": "Accession number is required." } ] }
```

**Copy status change — reason required for Lost/Damaged/Withdrawn**
```json
{ "status": "Damaged", "reason": "Water damage reported by student." }
```

---

## 5. Members (`members` module)

| Method | Path | Permission |
|---|---|---|
| GET | `/members/` | members.view — `?search=&department=&academicYear=&status=&blocked=true` |
| POST | `/members/` | members.create |
| GET | `/members/{rollNumber}/` | members.view |
| PUT/PATCH | `/members/{rollNumber}/` | members.edit |
| DELETE | `/members/{rollNumber}/` | members.delete — `400 MEMBER_HAS_HISTORY` if referenced elsewhere |
| GET | `/members/{rollNumber}/loans/` | members.view — `?status=Active` |
| GET | `/members/{rollNumber}/fines/` | members.view |
| POST | `/members/{rollNumber}/block/` | members.edit — `{ "reason": "..." }` |
| POST | `/members/{rollNumber}/unblock/` | members.edit |
| POST / DELETE | `/members/{rollNumber}/block-override/` | circulation.edit — POST `{ "reason": "..." }`, DELETE revokes it |
| GET | `/members/{rollNumber}/clearance/` | reports.view |

**Create member — request**
```json
{
  "rollNumber": "2026150", "name": "New Student", "department": "B.Sc. Chemistry",
  "academicYear": "1st Year", "email": "new.student@pscollege.ac.in", "phone": "9876543210",
  "status": "Active", "createLogin": true, "password": "firstlogin123"
}
```
**Response `201`** — a `MemberSerializer` payload including a computed `blockStatus`:
```json
{
  "id": 5, "rollNumber": "2026150", "name": "New Student", "department": "B.Sc. Chemistry",
  "academicYear": "1st Year", "email": "new.student@pscollege.ac.in", "phone": "9876543210",
  "status": "Active", "isBlocked": false, "blockReason": "", "blockOverride": null,
  "blockStatus": { "isBlocked": false, "isOverridden": false, "reasons": [], "primaryReason": null, "pendingFineTotal": 0, "maxOverdueDays": 0 },
  "activeLoanCount": 0, "hasLogin": true, "joinDate": "2026-10-05", "avatarUrl": ""
}
```

**Clearance — `GET /members/{rollNumber}/clearance/`**
```json
{
  "rollNumber": "2026902", "name": "Bikash Panda", "department": "B.A. English", "academicYear": "2nd Year",
  "cleared": true, "activeLoans": [], "overdueLoans": [], "pendingFines": [], "pendingFineTotal": 0,
  "heldItems": [], "dues": [], "certificateNo": "CLR-20261005-2026902"
}
```
When `cleared` is `false`, `certificateNo` is omitted and `dues` lists the blockers, e.g.
`["1 book(s) not returned (1 overdue)", "Unpaid fines ₹100 (1)"]`.

---

## 6. Circulation — Loans & Fines (`circulation` / `fines` modules)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/loans/issue/` | circulation.create | |
| GET | `/loans/{id}/return-preview/` | circulation.edit | `{ overdueDays, fineAmount }` before confirming |
| POST | `/loans/{id}/return/` | circulation.edit | |
| POST | `/loans/return-by-barcode/` | circulation.edit | `{ "copyBarcode": "..." }` — resolves the active loan |
| POST | `/loans/{id}/renew/` | circulation.edit | |
| GET | `/loans/` | circulation.view | `?status=&rollNumber=&accessionNumber=&overdue=true&issuedToday=true&dueToday=true&issueDateAfter=&issueDateBefore=&search=` |
| GET | `/loans/active/` `/loans/returned/` `/loans/overdue/` | circulation.view | same filters, pre-scoped |
| GET | `/loans/transactions/` | circulation.view | `?limit=50`, newest first |
| GET | `/loans/{id}/` | circulation.view | |
| GET | `/fines/` | fines.view | `?status=&rollNumber=&dateAfter=&dateBefore=&search=` |
| GET | `/fines/{id}/` | fines.view | includes the nested loan |
| POST | `/fines/{id}/collect/` | fines.edit | Pending → Collected |
| POST | `/fines/{id}/waive/` | fines.edit | `{ "reason": "..." }`, Pending → Waived |

**Issue a book — request**
```json
{ "rollNumber": "2026001", "accessionNumber": "PSC-0001", "copyBarcode": "PSC-0001-02" }
```
`copyBarcode` is optional — omit it to auto-pick the lowest-numbered available copy.

**Response `201`**
```json
{
  "id": 177, "rollNumber": "2026001", "memberName": "Ankit Rout", "department": "B.Sc. Physics",
  "accessionNumber": "PSC-0001", "bookId": 31, "bookTitle": "Indian Literature — Volume 1",
  "copyBarcode": "PSC-0001-02", "issueDate": "2026-10-05", "dueDate": "2026-10-19",
  "returnDate": null, "status": "Active", "renewalCount": 0, "fineId": null, "bookingId": null,
  "overdueDays": 0, "accruedFine": 0.0, "canRenew": { "allowed": true, "reason": null }
}
```
**Errors:** `400 MEMBER_INACTIVE`, `400 MEMBER_BLOCKED`, `400 BOOK_RETIRED`, `400 LIBRARY_USE_ONLY`,
`400 COPY_NOT_FOUND` / `COPY_ALREADY_ISSUED` / `COPY_NOT_ISSUABLE` / `COPY_HELD*`,
`400 NO_COPIES_AVAILABLE`, `400 LOAN_LIMIT_REACHED`.

**Return a book — response `200`**
```json
{
  "loan": { "...": "LoanSerializer shape, status: Returned" },
  "fineAmount": 10.0,
  "fine": { "id": 44, "loanId": 177, "rollNumber": "2026001", "memberName": "Ankit Rout", "bookTitle": "...", "overdueDays": 5, "amount": 10.0, "reason": "", "status": "Pending", "createdDate": "2026-10-05", "collectedDate": null, "actionedByName": null },
  "reservationPromoted": true
}
```
`fine` is `null` when `fineAmount` is `0` (returned on time). `reservationPromoted` tells you whether
the freed copy went to the next person waiting instead of back to "Available".

**Waive a fine**
```json
{ "reason": "Medical emergency — leave documentation on file" }
```

---

## 7. Book Requests (`book_requests`, gated under `circulation`)

| Method | Path | Permission |
|---|---|---|
| GET | `/book-requests/` | circulation.view — `?status=&rollNumber=` |
| POST | `/book-requests/{id}/approve/` | circulation.create |
| POST | `/book-requests/{id}/reject/` | circulation.create — optional `{ "reason": "..." }` |
| POST | `/book-requests/{id}/cancel/` | circulation.create |

Students create/cancel their own requests via `/student/book-requests/` (§12). Note the frontend-ported
asymmetry: open requests do **not** count against `maxConcurrentLoans` the way Bookings do.

---

## 8. Reservations (`reservations` module)

| Method | Path | Permission |
|---|---|---|
| GET | `/reservations/` | reservations.view — `?status=&accessionNumber=&rollNumber=` |
| POST | `/reservations/` | reservations.create — `{ "rollNumber": "...", "accessionNumber": "..." }` |
| POST | `/reservations/{id}/cancel/` | reservations.edit |

A reservation is a FIFO waitlist entry for a title with 0 copies available; it only *holds* a specific
copy once promoted to `Ready` (right after someone returns a copy of that title).

---

## 9. Bookings (`bookings` / `bookingAudit` modules)

The "reserve online, collect at the desk" flow: `Booked → Verified → Issued → Returned`, or `Cancelled`.

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET | `/bookings/` | bookings.view | `?status=&rollNumber=&dateAfter=&dateBefore=&search=` |
| GET | `/bookings/{bookingNo}/` | bookings.view | |
| POST | `/bookings/lookup/` | bookings.create | `{ "bookingNo": "...", "rollNumber": "..." }`, read-only desk check |
| POST | `/bookings/{bookingNo}/verify/` | bookings.create | optional `{ "rollNumber": "..." }` |
| POST | `/bookings/{bookingNo}/issue/` | bookings.create | auto-verifies if still `Booked`; returns `{ booking, loan }` |
| POST | `/bookings/{bookingNo}/cancel/` | bookings.edit | `{ "reason": "..." }` **required** for staff |
| GET | `/booking-audit/` | bookingAudit.view | `?bookingNo=&action=&role=&dateAfter=&dateBefore=` — **read-only, no writes exist** |

**Booking object shape**
```json
{
  "id": 12, "bookingNo": "BK-2026-000006", "rollNumber": "2026001", "studentName": "Ankit Rout",
  "accessionNumber": "PSC-0013", "book": 43, "bookTitle": "Microeconomics — Volume 13",
  "bookingDate": "2026-10-05", "expiryDate": "2026-10-07", "status": "Booked",
  "heldCopyBarcode": "PSC-0013-02", "updatedAt": "2026-10-05T20:52:31+05:30",
  "verifiedByName": "", "verifiedAt": null, "issuedByName": "", "issuedAt": null,
  "loanId": null, "returnedAt": null, "cancelledByName": "", "cancelledAt": null,
  "cancellationReason": "", "isExpired": false
}
```

**Errors from `lookup`/`verify`/`issue`:** `400 BOOKING_NOT_FOUND`, `BOOKING_STUDENT_MISMATCH`,
`BOOKING_EXPIRED` (also self-heals the expiry on the spot), `BOOKING_CANCELLED`,
`BOOKING_ALREADY_ISSUED`, `BOOKING_ALREADY_RETURNED`.

**Audit entry shape** (append-only — created automatically by every booking action, never written directly)
```json
{ "id": 14, "userId": null, "userName": "System", "role": "system", "actionTime": "2026-10-05T20:50:22+05:30", "action": "Issue", "bookingNo": "BK-2026-000003", "cancellationReason": "", "details": "Issued copy PSC-0004-02, due 2026-10-19" }
```

---

## 10. Notices (`notices` module)

| Method | Path | Permission |
|---|---|---|
| GET | `/notices/` | notices.view — `?category=&active=true` |
| POST | `/notices/` | notices.create |
| GET/PUT/PATCH | `/notices/{id}/` | notices.view / notices.edit |
| DELETE | `/notices/{id}/` | notices.delete |

```json
{ "title": "Library closed for inventory", "content": "...", "category": "Library Notices", "publishDate": "2026-10-10", "expiryDate": "2026-10-15" }
```
`expiryDate` (if given) must be on or after `publishDate` (`400 VALIDATION_ERROR` otherwise).

---

## 11. E-Books (`books` module, same permissions as physical books)

| Method | Path | Permission |
|---|---|---|
| GET | `/ebooks/` | books.view — `?publishStatus=&classification=&search=` |
| POST | `/ebooks/` (multipart) | books.create |
| GET/PUT/PATCH | `/ebooks/{id}/` | books.view / books.edit |
| DELETE | `/ebooks/{id}/` | books.delete — also deletes the file |
| POST | `/ebooks/{id}/publish/` | books.edit — `{ "isPublished": true }` |
| GET | `/ebooks/{id}/file/` | books.view — streams the actual file (staff preview; doesn't count as a read) |

Unlike the old frontend (which used a fake blob URL), `file` is a **real upload** (PDF/EPUB, ≤50MB by
default). `fileUrl` in responses always points at the protected `/file/` endpoint, never a raw media path.

---

## 12. Student self-service (`/student/...`)

Every endpoint here requires a `student` role with a linked `Member`, and is scoped to that member only —
another student's record returns `404`, not `403` (no way to even detect it exists).

| Method | Path | Notes |
|---|---|---|
| GET | `/student/me/` | profile + `activeLoans`/`openBookings`/`maxConcurrentLoans`/`slotsLeft` |
| GET | `/student/dashboard/` | due-soon loans, pending fine total, open holds, latest notices |
| GET | `/student/catalogue/` | stream-filtered — `?search=&category=&onSyllabus=true&available=true` |
| GET | `/student/catalogue/{id}/` | 404 if not visible to the student's stream |
| GET | `/student/loans/` | `?status=Active` |
| POST | `/student/loans/{id}/renew/` | |
| GET | `/student/fines/` | |
| GET/POST | `/student/bookings/` | POST `{ "accessionNumber": "..." }` |
| PATCH | `/student/bookings/{bookingNo}/` | swap the booked title, `{ "accessionNumber": "..." }` |
| POST | `/student/bookings/{bookingNo}/cancel/` | only while still `Booked` |
| GET/POST | `/student/book-requests/` | |
| POST | `/student/book-requests/{id}/cancel/` | |
| GET/POST | `/student/reservations/` | |
| POST | `/student/reservations/{id}/cancel/` | |
| GET | `/student/ebooks/` | published + stream-visible only |
| POST | `/student/ebooks/{id}/open/` | increments the read counter, returns `{ "fileUrl": "..." }` |
| GET | `/student/ebooks/{id}/file/` | streams the file |
| GET | `/student/notices/` | live (published, non-expired) only — `?category=` |
| GET | `/student/clearance/` | own clearance status |

All server-side business rules (stream/syllabus visibility, one-copy-per-title, loan/booking limits) are
re-validated here — the frontend's equivalent client-side checks were cosmetic only.

---

## 13. Reports (`reports` module, all read-only)

| Method | Path | Notes |
|---|---|---|
| GET | `/reports/dashboard-summary/` | everything the Dashboard page needs, in one call |
| GET | `/reports/holdings/` | titles/copies by category |
| GET | `/reports/category-distribution/` | book count by category (excludes Retired) |
| GET | `/reports/monthly-circulation/?months=6` | issued/returned/renewals per month |
| GET | `/reports/department-usage/` | loan count by borrower's department |
| GET | `/reports/overdue/?limit=5` | `{ buckets: [...], watchlist: [...] }` |
| GET | `/reports/top-borrowed/?days=30&limit=5` | |
| GET | `/reports/fines-breakdown/` | pending/collected/waived totals + counts |
| GET | `/reports/reservations-by-status/` | `{ ready, waiting }` |
| GET | `/reports/issue-return-summary/` | all-time counts |
| GET | `/reports/fine-collection/?from=&to=` | collected-fine rows + total |
| GET | `/reports/fine-register/?status=&from=&to=&rollNumber=&department=&groupBy=student` | |
| GET | `/reports/clearance/?rollNumber=` or `?department=&academicYear=` | single member, or a filtered batch |

---

## 14. Business rules appendix

| # | Rule | Where enforced |
|---|---|---|
| 1 | `fineAmount = min(overdueDays × finePerDay, maxFinePerBook)`; due date itself is not overdue | `circulation/calculators.py:calculate_fine` |
| 2 | `dueDate = issueDate + loanPeriodDays`; renewal extends from the **current** due date, not today | `calculate_due_date`, `calculate_renewed_due_date` |
| 3 | A member is blocked if: manually flagged, OR pending fines > `blockFineThreshold`, OR any active loan overdue > `blockOverdueDays`. A `blockOverride` doesn't clear the condition — it just lets issuing proceed anyway | `members/services.py:evaluate_block_status` |
| 4 | Issue validates: member active & not blocked, book not retired/library-only, copy resolvable & not held by someone else, under `maxConcurrentLoans` | `circulation/services.py:issue_book` |
| 5 | Return computes the fine, promotes the next reservation (or frees the copy), and closes any linked booking | `circulation/services.py:return_book` |
| 6 | `Book.availableCopies`/`status` are **recomputed** from live copy rows on every copy-status change — never incremented/decremented by hand | `catalogue/services.py:_sync_book_counts` |
| 7 | Booking: one copy held per booking, sequential never-reused `bookingNo`, counts against the **same** cap as loans, full audit trail | `bookings/services.py` |
| 8 | Reservation: FIFO waitlist; only the front-of-queue member's copy is held, and specifically *that* copy (fixing a bug in the old frontend, which released "any" held copy) | `reservations/services.py` |
| 9 | BookRequest: simpler parallel flow to Booking; open requests do **not** count against `maxConcurrentLoans` (an intentional asymmetry carried over from the original spec) | `book_requests/services.py` |
| 10 | Clearance: cleared only with zero active loans, zero pending fines, and no held booking/request/reservation | `reports/clearance.py` |
| 11 | One copy per title per student, enforced across Booking + Loan + BookRequest (not Reservation) | `circulation/services.py:assert_no_duplicate_title` |
| 12 | Barcodes (`{accession}-{NN}`) and booking numbers (`BK-{year}-{NNNNNN}`) are server-generated and concurrency-safe | `catalogue/services.py`, `bookings/services.py:next_booking_no` |
| 13 | A student only sees/books titles in their stream (by department) or explicitly tagged on their syllabus | `core/stream.py` |
| 14 | Bulk CSV import validates each row independently; a bad row is skipped, not fatal to the batch | `catalogue/services.py:bulk_import_books` |
| 15 | All dashboard/report numbers are real database aggregations, not client-side loops over the full dataset | `reports/selectors.py` |

### Status transitions

| Entity | Transitions |
|---|---|
| `BookCopy` | Available ↔ Held ↔ Issued; Available → Lost/Damaged/Withdrawn (manual, requires a reason) |
| `Loan` | Active → Returned (one-way) |
| `Fine` | Pending → Collected \| Waived (one-way) |
| `Booking` | Booked → Verified → Issued → Returned; Booked/Verified → Cancelled |
| `Reservation` | Waiting → Ready → Fulfilled \| Expired; any open state → Cancelled |
| `BookRequest` | Pending → Approved → Issued; Pending → Rejected; Approved/Pending → Cancelled/Expired |

### Error code reference

| Code | Meaning |
|---|---|
| `VALIDATION_ERROR` | Serializer field errors (see `fields` in the response) |
| `NOT_AUTHENTICATED` / `PERMISSION_DENIED` / `NOT_FOUND` | Standard auth/authz/404 |
| `ACCOUNT_SUSPENDED` | Login attempt on a suspended account |
| `MEMBER_INACTIVE` / `MEMBER_BLOCKED` / `MEMBER_NOT_FOUND` / `MEMBER_HAS_HISTORY` | Member-related |
| `BOOK_RETIRED` / `LIBRARY_USE_ONLY` / `BOOK_HAS_HISTORY` | Book-related |
| `COPY_NOT_FOUND` / `COPY_ALREADY_ISSUED` / `COPY_NOT_ISSUABLE` / `COPY_HELD` / `COPY_HELD_FOR_BOOKING` / `COPY_HELD_FOR_OTHER` / `COPY_IN_CIRCULATION` / `NO_COPIES_AVAILABLE` / `INSUFFICIENT_AVAILABLE_COPIES` | Copy-related |
| `LOAN_LIMIT_REACHED` / `LOAN_ALREADY_RETURNED` / `ACTIVE_LOAN_NOT_FOUND` / `RENEWAL_BLOCKED` | Loan-related |
| `FINE_NOT_PENDING` | Fine already collected/waived |
| `DUPLICATE_TITLE` / `OUT_OF_STREAM` / `BOOKING_LIMIT_REACHED` | Cross-flow eligibility |
| `BOOKING_NOT_FOUND` / `BOOKING_STUDENT_MISMATCH` / `BOOKING_EXPIRED` / `BOOKING_CANCELLED` / `BOOKING_ALREADY_ISSUED` / `BOOKING_ALREADY_RETURNED` / `BOOKING_NOT_EDITABLE` / `BOOKING_NOT_OPEN` / `NOT_YOUR_BOOKING` / `CANNOT_CANCEL` | Booking-related |
| `REQUEST_NOT_PENDING` | Book request already actioned |
| `REASON_REQUIRED` | A mandatory reason (waive/override/staff-cancel/manual copy status) was blank |

---

## 15. Scheduled jobs & seeding

- **`python manage.py expire_holds [--date YYYY-MM-DD] [--dry-run]`** — expires overdue-to-collect
  bookings, approved book requests, and ready reservations (in that order, so freed copies cascade to
  waitlists). Idempotent; intended to run every 10–15 minutes via cron / Windows Task Scheduler. Defense
  in depth: `issue_book`/`lookup_booking` also self-heal an expired-but-unswept booking on the spot.
- **`python manage.py seed_demo_data [--reset] [--seed 42]`** — rebuilds a realistic demo dataset
  (users, members, books/copies, loans/fines across every status, reservations, book requests, bookings
  across every status with a full audit trail, notices, sample e-books) using the real service functions,
  so every invariant holds automatically. `--reset` wipes existing data first.

---

## Changelog

- **1.0.0** — initial release: full Django REST Framework backend covering auth, catalogue, members,
  circulation, bookings, reservations, book requests, notices, e-books, reports, and student
  self-service, replacing the original frontend-only (localStorage) prototype.
