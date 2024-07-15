"""Testing settings configuration for Sub365 project."""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Testing-specific settings
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}
