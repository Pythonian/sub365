#!/bin/sh

until cd /home/app/web
do
    echo "Waiting for web volume..."
done

until python manage.py migrate
do
    echo "Waiting for db to be ready..."
    sleep 2
done

gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 4


# NOTE: Update the file permissions locally
# chmod +x docker/web-entrypoint.sh
