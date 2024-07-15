"""Module for Django management command to generate unique access codes."""

import random
import string

from django.core.management.base import BaseCommand

from accounts.models import AccessCode


class Command(BaseCommand):
    """Management command to generate unique access codes."""

    help = "Generate unique access codes"

    def add_arguments(self, parser):
        """Add command line arguments for the number of access codes to generate."""
        parser.add_argument(
            "num_codes",
            type=int,
            help="Number of access codes to generate",
        )

    def handle(self, *args, **options):
        """Handle command execution."""
        num_codes = options["num_codes"]
        generated_codes = set()

        while len(generated_codes) < num_codes:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
            if (
                not AccessCode.objects.filter(code=code).exists()
                and code not in generated_codes
            ):
                generated_codes.add(code)

        for code in generated_codes:
            AccessCode.objects.create(code=code)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated {len(generated_codes)} access codes.",
            ),
        )
