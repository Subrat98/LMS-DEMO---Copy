# LMS Backend

Django REST Framework backend for the Library Management System. Replaces the original
frontend-only (localStorage) prototype in `../LMS` with a real, server-enforced API — see
[`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) for the full endpoint reference, or run the
server and open `/api/docs` for interactive Swagger.

## Setup

```bash
cd LMS-Backend
python -m venv venv
./venv/Scripts/activate        # Windows; `source venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt

cp .env.example .env            # adjust DJANGO_SECRET_KEY etc. for anything beyond local dev

python manage.py migrate
python manage.py seed_demo_data     # creates demo users, members, books, loans, fines, bookings...
python manage.py runserver
```

Then visit:
- `http://localhost:8000/api/docs` — interactive Swagger UI
- `http://localhost:8000/admin` — Django admin (log in with the seeded `admin`/`admin123`)

Demo logins are printed at the end of `seed_demo_data`, and listed in `API_DOCUMENTATION.md` §1.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Scheduled cleanup

`python manage.py expire_holds` expires overdue-to-collect bookings/requests/reservations. Run it
every 10–15 minutes via cron or Windows Task Scheduler (`scripts/run_expire_holds.bat` is a starting
point for the latter). It's idempotent and safe to run as often as you like.

## Project layout

One Django project (`config/`) plus one app per frontend domain under `apps/` — `core` (shared
permission matrix, enums, exceptions), `accounts`, `library_settings`, `members`, `catalogue`
(books/copies), `reservations`, `book_requests`, `circulation` (loans/fines), `bookings`, `notices`,
`ebooks`, `reports` (read-only aggregations, no models), `student` (self-service views, no models).

Business logic lives only in each app's `services.py` (mutating, transactional, raises
`core.exceptions.BusinessRuleError` on a blocked action) — views and serializers just parse input,
call one service function, and serialize the result.

## Database

SQLite by default (`db.sqlite3`, gitignored). To move to Postgres, set `DATABASES["default"]` in
`config/settings.py` (or wire up `DATABASE_URL` via `dj-database-url`) — nothing else in the codebase
assumes SQLite.
