#!/bin/bash

set -o errexit
set -o nounset

worker_ready() {
    celery -A config.celery inspect ping
}

until worker_ready; do
  >&2 echo 'Celery workers not available'
  sleep 10
done
>&2 echo 'Celery workers is available'

celery -A config.celery  \
       --broker="${CELERY_BROKER_URL}" \
       flower

# NOTE: Update the file permissions locally
# chmod +x docker/flower-entrypoint.sh
