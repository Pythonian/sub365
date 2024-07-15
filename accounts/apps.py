"""Django application configuration for the 'accounts' app."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration class for the 'accounts' Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        """This method imports signals for the app's functionality."""
        import accounts.signals  # noqa: F401
