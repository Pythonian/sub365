from django.test import TestCase

from ..models import AccessCode


class AccessCodeTestCase(TestCase):
    """Test case for the string representation of the AccessCode model."""

    def test_access_code_string_representation(self):
        """Test the string representation of an AccessCode instance."""
        # Create an AccessCode instance
        access_code = AccessCode.objects.create(code="ABCDE")

        # Check the string representation
        self.assertEqual(str(access_code), "ABCDE")
