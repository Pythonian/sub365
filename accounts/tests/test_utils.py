"""Test cases for utility functions."""

import hashlib
import hmac

from django.http import QueryDict
from django.test import RequestFactory, TestCase

from accounts.utils import create_hmac_signature, mk_paginator


class MkPaginatorTests(TestCase):
    """Test cases for the mk_paginator utility function."""

    def setUp(self) -> None:
        """Set up the test environment.

        Creates a request object for testing mk_paginator.
        """
        self.factory = RequestFactory()
        self.request = self.factory.get("/test-url/")

    def test_mk_paginator_valid_page(self) -> None:
        """Checks if the function correctly paginates items when the page number is valid."""
        items = range(1, 101)
        num_items = 10
        # Create a mutable QueryDict and assign it to self.request.GET
        self.request.GET = QueryDict(mutable=True)
        self.request.GET["page"] = "3"  # Valid page
        paginated_items = mk_paginator(self.request, items, num_items)
        assert list(paginated_items) == list(range(21, 31))

    def test_mk_paginator_invalid_page(self) -> None:
        """Checks if the function returns the first page when the page number is invalid."""
        items = range(1, 101)
        num_items = 10
        self.request.GET = QueryDict(mutable=True)
        self.request.GET["page"] = "invalid"  # Invalid page
        paginated_items = mk_paginator(self.request, items, num_items)
        # Should return the first page
        assert list(paginated_items) == list(range(1, 11))

    def test_mk_paginator_out_of_range_page(self) -> None:
        """Checks if the function returns the last page when the page number is out of range."""
        items = range(1, 101)
        num_items = 10
        self.request.GET = QueryDict(mutable=True)
        self.request.GET["page"] = "999"  # Page out of range
        paginated_items = mk_paginator(self.request, items, num_items)
        # Should return the last page
        assert list(paginated_items) == list(range(91, 101))


class HMACSignatureTests(TestCase):
    """Test cases for the create_hmac_signature utility function."""

    def test_create_hmac_signature(self) -> None:
        """Checks if the function correctly generates an HMAC signature."""
        data = "test_data"
        api_secret_key = "test_secret_key"  # noqa: S105
        expected_signature = hmac.new(
            bytes(api_secret_key, "latin-1"),
            bytes(data, "latin-1"),
            hashlib.sha512,
        ).hexdigest()
        signature = create_hmac_signature(data, api_secret_key)
        assert signature == expected_signature

    def test_create_hmac_signature_empty_data(self) -> None:
        """Checks if the function correctly handles empty data."""
        data = ""
        api_secret_key = "test_secret_key"  # noqa: S105
        expected_signature = hmac.new(
            bytes(api_secret_key, "latin-1"),
            bytes(data, "latin-1"),
            hashlib.sha512,
        ).hexdigest()
        signature = create_hmac_signature(data, api_secret_key)
        assert signature == expected_signature

    def test_create_hmac_signature_empty_secret_key(self) -> None:
        """Checks if the function correctly handles an empty secret key."""
        data = "test_data"
        api_secret_key = ""
        expected_signature = hmac.new(
            bytes(api_secret_key, "latin-1"),
            bytes(data, "latin-1"),
            hashlib.sha512,
        ).hexdigest()
        signature = create_hmac_signature(data, api_secret_key)
        assert signature == expected_signature

    def test_create_hmac_signature_unicode_data(self) -> None:
        """Checks if the function correctly handles Unicode data."""
        data = "unicode_öäü"
        api_secret_key = "test_secret_key"  # noqa: S105
        expected_signature = hmac.new(
            bytes(api_secret_key, "latin-1"),
            bytes(data, "latin-1"),
            hashlib.sha512,
        ).hexdigest()
        signature = create_hmac_signature(data, api_secret_key)
        assert signature == expected_signature
