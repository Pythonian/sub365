.DEFAULT_GOAL := help
ROOT_DIR := ./

hello:
	@echo "Hello, World!"

help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

clean: ## Clean up the project of unneeded files
	@echo "Cleaning up the project of unneeded files..."
	@rm -rf .tox .mypy_cache .ruff_cache *.egg-info dist .cache htmlcov coverage.xml .coverage
	@find . -name '*.pyc' -delete
	@find . -name 'db.sqlite3' -delete
	@find . -type d -name '__pycache__' -exec rm -r {} \+
	@echo "Clean up successfully completed."

run: ## Run the development server
	@python manage.py runserver

admin: ## Create admin superuser
	@python manage.py createsuperuser

shell: ## Start a Django shell
	@python manage.py shell

migrate: ## Run django db migrations
	@python manage.py makemigrations
	@python manage.py migrate

stripe: ## Listen to stripe webhook
	@stripe listen --forward-to localhost:8000/webhook/ --forward-connect-to localhost:8000/webhook/

beat: ## Start the celery beat
	@celery -A config.celery beat -l INFO

worker: ## Start the celery worker
	@celery -A config.celery worker -l INFO --concurrency 4 -E

accesscodes: ## Generate 50 access codes
	@python manage.py access_codes 50

backup: ## Backup data to JSON file
	@python manage.py dumpdata --indent 4 --format json accounts > dump.json
