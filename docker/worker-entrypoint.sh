#!/bin/sh

until cd /home/app/web
do
    echo "Waiting for web volume..."
done

celery -A config.celery worker -l INFO --concurrency 4 -E

# NOTE: Update the file permissions locally
# chmod +x docker/worker-entrypoint.sh
