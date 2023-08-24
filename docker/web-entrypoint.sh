#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python manage.py migrate

gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 4

# NOTE: Update the file permissions locally
# chmod +x docker/web-entrypoint.sh
