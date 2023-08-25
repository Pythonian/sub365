#!/bin/bash

set -o errexit
set -o nounset

# Wait for database migrations to be applied
until python manage.py migrate --check
do
    echo "Waiting for migrations to be applied..."
    sleep 10
done

rm -f './celerybeat.pid'
celery -A config.celery beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

# NOTE: Update the file permissions locally
# chmod +x docker/entrypoints/beat.sh
