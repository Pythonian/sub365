.DEFAULT_GOAL := help
ROOT_DIR := ./
PYTHON := docker-compose exec web python

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

run: ## Start project with docker
	@docker-compose up -d

build: ## Build docker containers
	@docker-compose up --build -d

createsuperuser: ## Create admin superuser
	@$(PYTHON) manage.py createsuperuser

shell: ## Start a Django shell
	@$(PYTHON) manage.py shell

test: ## Run tests with coverage
	@$(PYTHON) -m coverage run --source='.' manage.py test
	@$(PYTHON) -m coverage report -m

pipupdate: ## Update project requirements
	@$(PYTHON) manage.py pipupdates

accesscodes: ## Generate access codes
	@$(PYTHON) manage.py access_codes 20

down: ## Stop docker containers
	@docker-compose down
