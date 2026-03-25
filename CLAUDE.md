# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ModelForge is a Python microservice that generates 3D models from images. It consumes tasks from Kafka, downloads images from MinIO (S3-compatible), runs ML inference, and uploads results back to MinIO, tracking status in PostgreSQL.

## Build & Run Commands

### Full stack (from `deploy/` directory)
```bash
cp .env.example .env  # first time only
docker-compose -f docker-compose.yml -f docker-compose.infra.yml -f docker-compose.logging.yml -f docker-compose.app.yml up -d --build
```

### Infrastructure only (Kafka, PostgreSQL, MinIO, Zookeeper)
```bash
docker-compose -f docker-compose.yml -f docker-compose.infra.yml up -d
```

### Run tests
```bash
cd ml-service
PYTHONPATH=src pytest tests/ -v
```

### Run a single test
```bash
cd ml-service
PYTHONPATH=src pytest tests/test_processor.py -v -k "test_name"
```

### Seed test data (requires running infrastructure)
```bash
python ml-service/scripts/seed_minio.py   # uploads test images to MinIO
python ml-service/scripts/seed_tasks.py   # sends test tasks to Kafka
```

## Architecture

The system is a distributed pipeline with this data flow:

**Kafka** (task queue) → **ml-worker** (processing) → **MinIO** (artifact storage), with **PostgreSQL** for task state tracking and **Loki/Grafana/Promtail** for observability.

All application code lives in `ml-service/src/modelforge/` with these layers:

- **worker/** — Entry point (`main.py`) and application lifecycle (`app.py`) with signal handling
- **kafka/** — `KafkaConsumerService` polls `modelforge.generation.requests` topic
- **tasks/** — `TaskProcessor` orchestrates the pipeline: download image → run inference → upload results → update status
- **ml/** — ML inference behind `ModelInferenceInterface` ABC. `MockInferenceService` for dev/test, real implementations (e.g. TripoSR) to be added via `factory.py`
- **database/** — `TaskRepository` for PostgreSQL task state (PENDING → COMPLETED/FAILED)
- **storage/** — `S3StorageService` wraps boto3 for MinIO operations
- **config/** — Pydantic `BaseSettings` for env-based configuration; JSON/text logging setup

## Key Patterns

- **Factory pattern** in `ml/factory.py` — switches ML backend based on `ML_MOCK_MODE` env var
- **Strategy pattern** — `ModelInferenceInterface` allows swapping ML implementations
- **Constructor injection** — services are injected into `App` and `TaskProcessor`
- Configuration is entirely env-var driven via pydantic-settings (see `deploy/.env.example` for all variables)

## Language & Runtime

- Python 3.9, dependencies in `ml-service/requirements.txt`
- Docker images based on `python:3.9-slim`
- Commit messages are in Russian
