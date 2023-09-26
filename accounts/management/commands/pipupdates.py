import subprocess

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check for and update outdated Python packages using pip."

    def handle(self, *args, **options):
        try:
            # Use pip list to get a list of outdated packages
            outdated_packages = subprocess.check_output(
                ["pip", "list", "--outdated", "--format=columns"], universal_newlines=True
            )

            if not outdated_packages.strip():
                self.stdout.write(self.style.SUCCESS("All packages are up to date!"))
                return

            self.stdout.write("Outdated packages:")
            self.stdout.write(outdated_packages)

            # Ask the user if they want to update packages
            response = input("Do you want to update these packages? (y/n): ").strip().lower()

            if response == "y":
                # Upgrade outdated packages
                subprocess.call(
                    ["pip", "install", "--upgrade"]
                    + [line.split()[0] for line in outdated_packages.strip().split("\n")[2:]]
                )
                self.stdout.write(self.style.SUCCESS("Packages updated successfully!"))
            else:
                self.stdout.write(self.style.NOTICE("No packages were updated."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {str(e)}"))
