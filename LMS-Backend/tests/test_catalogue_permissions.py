"""Regression test for a real bug found during an access-control audit: the combined
GET/POST `/books/{id}/copies/` action was keyed by a single DRF `action` name, so both
reading copies and ADDING copies were checked against the same ("books", "view")
permission — meaning staff/principal (view-only on books) could add copies, which should
require "books.edit". Fixed by making HasModulePermission support a per-HTTP-method
dict for one action; this test locks that fix in.
"""

import pytest

pytestmark = pytest.mark.django_db


def test_staff_can_view_copies_but_not_add_them(api_client, staff_user, make_book):
    book = make_book(total_copies=1)
    client = api_client(staff_user)

    read_response = client.get(f"/api/v1/books/{book.id}/copies/")
    assert read_response.status_code == 200

    write_response = client.post(f"/api/v1/books/{book.id}/copies/", {"count": 1}, format="json")
    assert write_response.status_code == 403


def test_librarian_can_both_view_and_add_copies(api_client, librarian_user, make_book):
    book = make_book(total_copies=1)
    client = api_client(librarian_user)

    write_response = client.post(f"/api/v1/books/{book.id}/copies/", {"count": 2}, format="json")
    assert write_response.status_code == 201
    assert len(write_response.json()) == 2

    read_response = client.get(f"/api/v1/books/{book.id}/copies/")
    assert read_response.status_code == 200
    assert len(read_response.json()) == 3
