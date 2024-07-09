- ssh seyi@165.232.135.255
- cd webapp/server-subs && . venv/bin/activate
- git pull
- python manage.py migrate
- python manage.py check --deploy
- python manage.py collectstatic
- sudo systemctl restart gunicorn

- sudo systemctl status celerybeat

- ssh root@165.232.135.255
- su - seyi
- sudo -i -u postgres
- psql

root digitalocean pwd: sub365.co

Postgres Setup
- sudo service postgresql start
- sudo -u postgres psql
- CREATE DATABASE sub365db;
- CREATE USER sub365usr WITH PASSWORD '-qS!%$3?3&WvEj';
- ALTER ROLE sub365usr SET client_encoding TO 'utf8';
- ALTER ROLE sub365usr SET default_transaction_isolation TO 'read committed';
- ALTER ROLE sub365usr SET timezone TO 'UTC';
- GRANT ALL PRIVILEGES ON DATABASE sub365db TO sub365usr;

apt install python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx
apt install certbot python3-certbot-nginx

- https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04

- python -m pip install pre-commit
- touch .pre-commit-config.yaml
- Install git hook scripts: pre-commit install
- pre-commit run --all-files
- git add .
- git commit -m "msg"

sudo tail -f /var/log/nginx/access.log

sudo apt install stripe
stripe login
stripe listen --forward-to localhost:8000/webhook/ --forward-connect-to localhost:8000/webhook/
Check ngix conf is correct:  docker exec -ti nginx nginx -t
sudo nano /etc/nginx/sites-available/server-subs

sudo service redis-server start
celery -A config.celery beat -l INFO
celery -A config.celery worker -l INFO --concurrency 4 -E

python manage.py sqlmigrate accounts 0001_initial
DB diagram - https://dbdiagram.io/d/Sub365-65235e8affbf5169f047ea44

python manage.py dumpdata --indent 4 --format json accounts > dump.json
https://stripe.com/docs/api/errors/handling

python -c "import secrets; print(secrets.token_urlsafe())"
