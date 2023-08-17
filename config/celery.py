import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Prefix all celery-related configuration keys with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Update timezone
# app.conf.enable_utc = False
# app.conf.update(timezone="Africa/Lagos")

# Celery Beat Settings
# app.conf.beat_schedule = {

# }

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Add broker_connection_retry_on_startup setting
app.conf.broker_connection_retry_on_startup = True
