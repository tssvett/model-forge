# ============================================================
# ModelForge — Makefile
# ============================================================
# All docker-compose commands run from the deploy/ directory.
# Usage: make <target>
# ============================================================

COMPOSE = docker compose -f docker-compose.yml
INFRA   = $(COMPOSE) -f docker-compose.infra.yml
LOG     = $(INFRA) -f docker-compose.logging.yml
MON     = $(LOG) -f docker-compose.monitoring.yml
APP     = $(INFRA) -f docker-compose.app.yml
KOTLIN  = $(INFRA) -f docker-compose.kotlin.yml
FRONT   = $(KOTLIN) -f docker-compose.frontend.yml
FULL    = $(MON) -f docker-compose.app.yml -f docker-compose.kotlin.yml -f docker-compose.frontend.yml
GPU     = $(FULL) -f docker-compose.gpu.yml

# --- Initial setup ----------------------------------------------------------

.PHONY: init
init: ## Copy .env.example -> .env (first run)
	@test -f deploy/.env || cp deploy/.env.example deploy/.env
	@echo "deploy/.env ready — edit as needed"

# --- Start stacks -----------------------------------------------------------

.PHONY: infra
infra: ## Infrastructure: Kafka, PostgreSQL, MinIO, Zookeeper
	cd deploy && $(INFRA) up -d

.PHONY: app
app: ## Infrastructure + ML Worker
	cd deploy && $(APP) up -d --build

.PHONY: backend
backend: ## Infrastructure + Kotlin API + ML Worker
	cd deploy && $(APP) -f docker-compose.kotlin.yml up -d --build

.PHONY: full
full: ## Full stack: all services + logging
	cd deploy && $(FULL) up -d --build

.PHONY: gpu
gpu: ## Full stack with GPU for ML Worker (NVIDIA)
	cd deploy && $(GPU) up -d --build

.PHONY: monitoring
monitoring: ## Infrastructure + logging + monitoring (Prometheus, exporters)
	cd deploy && $(MON) up -d

.PHONY: dev
dev: ## Dev mode: infrastructure + logging + monitoring (services run locally)
	cd deploy && $(MON) up -d

# --- Stop -------------------------------------------------------------------

.PHONY: down
down: ## Stop all containers (data preserved)
	cd deploy && $(FULL) down 2>/dev/null; true

.PHONY: clean
clean: ## Stop everything and delete volumes (data lost!)
	cd deploy && $(FULL) down -v 2>/dev/null; true

# --- Logs -------------------------------------------------------------------

.PHONY: logs
logs: ## Tail logs for all services
	cd deploy && $(FULL) logs -f --tail=100

.PHONY: logs-ml
logs-ml: ## Tail ML Worker logs
	cd deploy && $(APP) logs -f ml-worker

.PHONY: logs-kotlin
logs-kotlin: ## Tail Kotlin Service logs
	cd deploy && $(KOTLIN) logs -f kotlin-service

.PHONY: logs-kafka
logs-kafka: ## Tail Kafka logs
	cd deploy && $(INFRA) logs -f kafka

# --- Testing ----------------------------------------------------------------

.PHONY: test-ml
test-ml: ## Run ML Service tests
	cd ml-service && PYTHONPATH=src pytest tests/ -v

.PHONY: test-kotlin
test-kotlin: ## Run Kotlin Service tests
	cd kotlin-service && ./gradlew check

.PHONY: test-frontend
test-frontend: ## Build frontend (verification)
	cd frontend && npm ci && npm run build

.PHONY: test
test: test-ml test-kotlin test-frontend ## Run all tests

# --- Seed data --------------------------------------------------------------

.PHONY: seed
seed: ## Upload test data to MinIO and Kafka
	cd ml-service && python scripts/seed_minio.py && python scripts/seed_tasks.py

# --- Build images -----------------------------------------------------------

.PHONY: build
build: ## Build all Docker images without starting
	cd deploy && $(FULL) build

.PHONY: build-ml
build-ml: ## Build ML Service Docker image
	cd ml-service && docker build -t modelforge-ml-service:latest .

.PHONY: build-kotlin
build-kotlin: ## Build Kotlin Service Docker image
	cd kotlin-service && docker build -t modelforge-kotlin-service:latest .

.PHONY: build-frontend
build-frontend: ## Build Frontend Docker image
	cd frontend && docker build -t modelforge-frontend:latest .

# --- Utilities --------------------------------------------------------------

.PHONY: ps
ps: ## Show container status
	cd deploy && $(FULL) ps 2>/dev/null; true

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
