"""Development settings configuration for Sub365 project."""

from .base import *

DEBUG = config("DEBUG", cast=bool, default=True)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv(), default=["localhost", "127.0.0.1"])

INSTALLED_APPS += [
    # Additional apps for development
    "debug_toolbar",
]

MIDDLEWARE += [
    # Additional middleware for development
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INTERNAL_IPS = [
    "127.0.0.1",
]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
