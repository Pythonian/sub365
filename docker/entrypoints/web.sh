#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python manage.py migrate --no-input
python manage.py collectstatic --no-input

gunicorn --worker-tmp-dir /dev/shm config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 4

# NOTE: Update the file permissions locally
# chmod +x docker/entrypoints/web.sh
