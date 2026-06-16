.DEFAULT_GOAL := help

.PHONY: help install run test lint type-check security-scan docker-build docker-up

help:
	@echo "Available commands:"
	@echo "  make install       Install dependencies with Poetry"
	@echo "  make run           Start the Flask development server"
	@echo "  make test          Run unit tests with coverage"
	@echo "  make lint          Run Ruff linter"
	@echo "  make type-check    Run mypy type checker"
	@echo "  make security-scan Run Bandit (SAST) + Safety (CVE)"
	@echo "  make docker-build  Build API + Worker Docker images"
	@echo "  make docker-up     Start full stack with docker-compose"

install:
	pip install poetry
	poetry install

run:
	poetry run python run.py

test:
	poetry run pytest

lint:
	poetry run ruff check src/ tests/

type-check:
	poetry run mypy src/

security-scan:
	poetry run bandit -r src/ -ll
	poetry run safety check

docker-build:
	docker build -f deployment/docker/Dockerfile.api -t hubb-api:dev .
	docker build -f deployment/docker/Dockerfile.worker -t hubb-worker:dev .

docker-up:
	docker compose -f deployment/docker/docker-compose.yml up --build
