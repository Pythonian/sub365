import hashlib
import hmac

from django.http import QueryDict
from django.test import RequestFactory, TestCase

from accounts.utils import create_hmac_signature, mk_paginator


class UtilityFunctionTests(TestCase):
    def setUp(self):
        # Create a request object for testing mk_paginator
        self.factory = RequestFactory()
        self.request = self.factory.get("/test-url/")

    def test_mk_paginator_valid_page(self):
        # Test when the page is a valid integer
        items = range(1, 101)
        num_items = 10
        # Create a mutable QueryDict and assign it to self.request.GET
        self.request.GET = QueryDict(mutable=True)
        self.request.GET["page"] = "3"  # Valid page
        paginated_items = mk_paginator(self.request, items, num_items)
        self.assertEqual(list(paginated_items), list(range(21, 31)))

    def test_mk_paginator_invalid_page(self):
        # Test when the page is not an integer
        items = range(1, 101)
        num_items = 10
        self.request.GET = QueryDict(mutable=True)
        self.request.GET["page"] = "invalid"  # Invalid page
        paginated_items = mk_paginator(self.request, items, num_items)
        # Should return the first page
        self.assertEqual(list(paginated_items), list(range(1, 11)))

    def test_mk_paginator_out_of_range_page(self):
        # Test when the page is out of range
        items = range(1, 101)
        num_items = 10
        self.request.GET = QueryDict(mutable=True)
        self.request.GET["page"] = "999"  # Page out of range
        paginated_items = mk_paginator(self.request, items, num_items)
        # Should return the last page
        self.assertEqual(list(paginated_items), list(range(91, 101)))

    def test_create_hmac_signature(self):
        # Test create_hmac_signature function
        data = "test_data"
        api_secret_key = "test_secret_key"
        expected_signature = hmac.new(
            bytes(api_secret_key, "latin-1"), bytes(data, "latin-1"), hashlib.sha512
        ).hexdigest()
        signature = create_hmac_signature(data, api_secret_key)
        self.assertEqual(signature, expected_signature)

    def test_create_hmac_signature_empty_data(self):
        # Test create_hmac_signature with empty data
        data = ""
        api_secret_key = "test_secret_key"
        expected_signature = hmac.new(
            bytes(api_secret_key, "latin-1"), bytes(data, "latin-1"), hashlib.sha512
        ).hexdigest()
        signature = create_hmac_signature(data, api_secret_key)
        self.assertEqual(signature, expected_signature)

    def test_create_hmac_signature_empty_secret_key(self):
        # Test create_hmac_signature with empty secret key
        data = "test_data"
        api_secret_key = ""
        expected_signature = hmac.new(
            bytes(api_secret_key, "latin-1"), bytes(data, "latin-1"), hashlib.sha512
        ).hexdigest()
        signature = create_hmac_signature(data, api_secret_key)
        self.assertEqual(signature, expected_signature)

    def test_create_hmac_signature_unicode_data(self):
        # Test create_hmac_signature with unicode data
        data = "unicode_öäü"
        api_secret_key = "test_secret_key"
        expected_signature = hmac.new(
            bytes(api_secret_key, "latin-1"), bytes(data, "latin-1"), hashlib.sha512
        ).hexdigest()
        signature = create_hmac_signature(data, api_secret_key)
        self.assertEqual(signature, expected_signature)
