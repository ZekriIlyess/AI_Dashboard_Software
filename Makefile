# =============================================================================
# Nexus AI - Makefile
# =============================================================================
# Common commands for development, testing, and deployment.
# Usage: make <target>
# =============================================================================

.PHONY: help dev dev-backend dev-frontend dev-infra test lint build clean

# Default target
help: ## Show this help message
	@echo.
	@echo  Nexus AI - Development Commands
	@echo  ================================
	@echo.
	@echo  DEVELOPMENT
	@echo    make dev              Start everything (infra + backend + frontend)
	@echo    make dev-infra        Start infrastructure only (PostgreSQL, Redis)
	@echo    make dev-backend      Start backend only (FastAPI)
	@echo    make dev-frontend     Start frontend only (Next.js)
	@echo    make dev-stop         Stop all infrastructure
	@echo.
	@echo  TESTING
	@echo    make test             Run all tests
	@echo    make test-backend     Run backend tests only
	@echo    make test-frontend    Run frontend tests only
	@echo.
	@echo  CODE QUALITY
	@echo    make lint             Lint all code
	@echo    make format           Format all code
	@echo.
	@echo  DATABASE
	@echo    make db-migrate       Create new migration
	@echo    make db-upgrade       Run migrations
	@echo    make db-seed          Seed test data
	@echo.
	@echo  DOCKER
	@echo    make build            Build all Docker images
	@echo    make up               Start production stack
	@echo    make down             Stop production stack
	@echo.

# =============================================================================
# Development
# =============================================================================

dev-infra: ## Start infrastructure (PostgreSQL, Redis)
	docker compose -f docker/docker-compose.yml up -d postgres redis

dev-backend: ## Start backend (FastAPI with hot reload)
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend (Next.js dev server)
	cd frontend && npm run dev

dev-stop: ## Stop infrastructure
	docker compose -f docker/docker-compose.yml down

# =============================================================================
# Testing
# =============================================================================

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd backend && python -m pytest tests/ -v --tb=short

test-frontend: ## Run frontend tests
	cd frontend && npm test

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Lint all code
	cd backend && python -m ruff check .
	cd frontend && npm run lint

format: ## Format all code
	cd backend && python -m ruff format .
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css}"

# =============================================================================
# Database
# =============================================================================

db-migrate: ## Create a new migration (usage: make db-migrate msg="add users table")
	cd backend && python -m alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Run all pending migrations
	cd backend && python -m alembic upgrade head

db-downgrade: ## Rollback last migration
	cd backend && python -m alembic downgrade -1

db-seed: ## Seed test database with sample data
	cd backend && python -m scripts.seed_test_db

# =============================================================================
# Docker
# =============================================================================

build: ## Build all Docker images
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml build

up: ## Start production stack
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d

down: ## Stop production stack
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down

logs: ## Tail production logs
	docker compose -f docker/docker-compose.yml logs -f

# =============================================================================
# Utilities
# =============================================================================

clean: ## Clean build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>nul
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>nul
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>nul
	if exist frontend\.next rmdir /s /q frontend\.next
	if exist frontend\node_modules rmdir /s /q frontend\node_modules

setup: ## First-time setup (install all dependencies)
	@echo Setting up Nexus AI development environment...
	copy .env.example .env
	docker compose -f docker/docker-compose.yml up -d postgres redis
	cd backend && python -m venv .venv && .venv\Scripts\pip install -e ".[dev]"
	cd frontend && npm install
	cd backend && python -m alembic upgrade head
	@echo.
	@echo  Setup complete! Run 'make dev-backend' and 'make dev-frontend' to start.
