# Makefile for Django project with Docker Compose

# Define the Docker Compose project name
COMPOSE_PROJECT_NAME = my-django-project

# Define the Docker Compose YAML file
COMPOSE_FILE = docker-compose.yml

build: # Build Docker containers defined in the Compose file
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) build

up: # Start Docker containers in detached mode
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) up -d

down: # Stop and remove all Docker containers and volumes
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) down -v

shell: # Access a shell inside the Django container
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) exec web bash

migrate: # Apply database migrations
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) exec web python manage.py migrate

createsuperuser: # Create a superuser for the Django admin
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) exec web python manage.py createsuperuser

collectstatic: # Collect static files
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) exec web python manage.py collectstatic --noinput

test: # Run tests
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) exec web python manage.py test

logs: # View logs from the Django container
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) logs -f

clean: # Clean up Docker resources (containers, volumes, and networks)
	docker-compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) down -v --remove-orphans

------------------------------

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
	@coverage run manage.py test accounts/tests/
	@coverage html

accesscodes: ## Generate access codes
	@$(PYTHON) manage.py access_codes 20

down: ## Stop docker containers
	@docker-compose down


-------------------

.DEFAULT_GOAL=help
ROOT_DIR:=./
VENV_BIN_DIR:="venv/bin"

VIRTUALENV:=$(shell which virtualenv)

REQUIREMENTS_DIR:="requirements"
REQUIREMENTS_LOCAL:="$(REQUIREMENTS_DIR)/development.txt"
REQUIREMENTS_DOCKER:="$(REQUIREMENTS_DIR)/docker.txt"

PIP:="$(VENV_BIN_DIR)/pip"
FLAKE8:="$(VENV_BIN_DIR)/flake8"
ISORT:="$(VENV_BIN_DIR)/isort"
AUTOPEP8:="$(VENV_BIN_DIR)/autopep8"

CMD_FROM_VENV:=". $(VENV_BIN_DIR)/activate; which"
PYTHON=$(shell "$(CMD_FROM_VENV)" "python")

# .PHONY: hello venv freeze check fix clean makemigrations migrate superuser runlocal

hello:
	@echo "Hello, World!"

help: # Show this help
	@egrep -h '\s#\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?# "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

define create-venv
python3 -m venv venv
endef

venv: # Create virtual environment
	@$(create-venv)

install: # Install dependencies
	@$(PIP) install -r $(REQUIREMENTS_LOCAL)

freeze: venv # Save project dependencies into requirements file
	@$(PIP) freeze > $(REQUIREMENTS_LOCAL)

check: venv # Format with Flake8 isort
	@$(FLAKE8) src
	@$(ISORT) -rc -c src

fix: venv
	@$(ISORT) -rc src
	@$(AUTOPEP8) --in-place --aggressive --recursive src

clean: # Cleans up the project of unneeded files
	@rm -rf .cache
	@rm -rf htmlcov coverage.xml .coverage
	@find . -name *.pyc -delete
	@find . -name db.sqlite3 -delete
	@find . -type d -name __pycache__ -exec rm -r {} \+
	@rm -rf venv
	@rm -rf .tox

test: # Run tests
	@python manage.py test

runmigrations: venv # Run database migrations
	@$(PYTHON) $(ROOT_DIR)/manage.py makemigrations $(app) --settings config.settings.local
	@$(PYTHON) $(ROOT_DIR)/manage.py migrate $(app) $(migration) --settings config.settings.local

superuser: venv # Create admin superuser
	@$(PYTHON) $(ROOT_DIR)/manage.py createsuperuser --settings config.settings.local

runlocal: venv # Run development server
	@$(PYTHON) $(ROOT_DIR)/manage.py runserver --settings=config.settings.local
	#@python manage.py runserver --settings=config.settings.development

rundocker:
	@docker-compose up --build

docs: # Install documentation related dependencies
	@$(PIP) install -r $(REQUIREMENTS_LOCAL)/docs.txt

serve-docs: # Serve docs on localhost
	@mkdocs serve -f docs/mkdocs.yml
