.DEFAULT_GOAL := help
ROOT_DIR := ./

hello:
	@echo "Hello, World!"

help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

clean: ## Clean up the project of unneeded files
	@rm -rf .cache
	@rm -rf htmlcov coverage.xml .coverage
	@find . -name '*.pyc' -delete
	@find . -name 'db.sqlite3' -delete
	@find . -type d -name '__pycache__' -exec rm -r {} \+
	@rm -rf .tox

run: ## Run the development server
	@python manage.py runserver

admin: ## Create admin superuser
	@python manage.py createsuperuser

shell: ## Start a Django shell
	@python manage.py shell

test: ## Run tests with coverage
	@coverage run manage.py test accounts/tests/
	@coverage html

accesscodes: ## Generate 20 access codes
	@python manage.py access_codes 20
