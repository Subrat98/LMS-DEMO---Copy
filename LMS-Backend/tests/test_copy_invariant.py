import pytest

from apps.catalogue import services as catalogue_services

pytestmark = pytest.mark.django_db


def _assert_invariant(book):
    book.refresh_from_db()
    assert book.available_copies == book.copies.filter(status="Available").count()
    assert book.total_copies == book.copies.count()


def test_available_copies_matches_after_create(make_book):
    book = make_book(total_copies=3)
    _assert_invariant(book)
    assert book.available_copies == 3
    assert book.status == "Available"


def test_available_copies_drops_to_zero_flips_status(make_book):
    book = make_book(total_copies=2)
    copies = list(book.copies.all())
    catalogue_services.set_copy_status(copies[0], "Issued")
    catalogue_services.set_copy_status(copies[1], "Issued")
    _assert_invariant(book)
    book.refresh_from_db()
    assert book.available_copies == 0
    assert book.status == "Fully Issued"


def test_releasing_a_copy_restores_available_status(make_book):
    book = make_book(total_copies=1)
    copy = book.copies.first()
    catalogue_services.set_copy_status(copy, "Issued")
    catalogue_services.set_copy_status(copy, "Available")
    _assert_invariant(book)
    book.refresh_from_db()
    assert book.status == "Available"


def test_retired_status_is_sticky_even_when_copies_available(make_book):
    book = make_book(total_copies=2)
    catalogue_services.retire_book(book)
    copy = book.copies.first()
    catalogue_services.set_copy_status(copy, "Lost")
    catalogue_services.set_copy_status(copy, "Available")
    book.refresh_from_db()
    assert book.status == "Retired"


def test_add_copies_numbers_sequentially(make_book):
    book = make_book(total_copies=2)
    new_copies = catalogue_services.add_copies(book, 2)
    numbers = sorted(c.copy_number for c in new_copies)
    assert numbers == [3, 4]
    _assert_invariant(book)


def test_hold_copy_raises_when_none_available(make_book):
    from apps.core.exceptions import BusinessRuleError

    book = make_book(total_copies=1)
    catalogue_services.set_copy_status(book.copies.first(), "Issued")
    with pytest.raises(BusinessRuleError):
        catalogue_services.hold_copy(book)
