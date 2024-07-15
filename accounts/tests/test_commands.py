"""Test case for the custom management command."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import AccessCode


class GenerateAccessCodesTest(TestCase):
    """Test case for the management command to generate access codes."""

    def test_generate_access_codes(self) -> None:
        """Test the generation of access codes."""
        # Define the number of codes to generate for the test
        num_codes_to_generate = 10

        # Execute the management command
        out = StringIO()
        call_command("access_codes", str(num_codes_to_generate), stdout=out)

        # Check if the access codes were generated and saved correctly
        generated_codes = AccessCode.objects.count()
        assert generated_codes == num_codes_to_generate

        # Check if the output message indicates successful generation
        expected_output = (
            f"Successfully generated {num_codes_to_generate} access codes."
        )
        assert expected_output in out.getvalue()
