# ModelForge ML Service

Python worker service for 3D model generation. Consumes tasks from Kafka, runs ML inference (TripoSR or mock), and uploads results to MinIO.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Testing](#testing)
- [ML Model Integration](#ml-model-integration)

## Overview

The ML Service is a long-running worker that:

- **Consumes generation requests** from Kafka topic `modelforge.generation.requests`
- **Downloads input images** from MinIO (S3-compatible storage)
- **Runs 3D inference** using TripoSR (GPU) or a mock service (dev/test)
- **Uploads generated GLB models** back to MinIO
- **Updates task status** in PostgreSQL (PENDING → PROCESSING → COMPLETED/FAILED)

```mermaid
graph LR
    KF[[Kafka]] -->|consume| Worker[ML Worker]
    Worker -->|download image| MIO[(MinIO)]
    Worker -->|run inference| ML[TripoSR / Mock]
    ML -->|GLB model| Worker
    Worker -->|upload result| MIO
    Worker -->|update status| PG[(PostgreSQL)]
```

## Architecture

All application code lives in `ml-service/src/modelforge/`:

```mermaid
graph TD
    subgraph Worker
        Main[worker/main.py — Entry point]
        App[worker/app.py — Lifecycle + signals]
    end

    subgraph Kafka
        Consumer[kafka/consumer.py — KafkaConsumerService]
    end

    subgraph Tasks
        Processor[tasks/processor.py — TaskProcessor]
    end

    subgraph ML
        Factory[ml/factory.py — create_inference_service]
        Interface[ml/interface.py — ModelInferenceInterface ABC]
        Mock[ml/mock_service.py — MockInferenceService]
        TripoSR[ml/triposr_service.py — TripoSRService]
    end

    subgraph Data
        Repo[database/repository.py — TaskRepository]
        Storage[storage/s3_service.py — S3StorageService]
    end

    subgraph Config
        Settings[config/settings.py — Pydantic BaseSettings]
        Logging[config/logging.py — JSON/text log setup]
    end

    Main --> App
    App --> Consumer
    Consumer --> Processor
    Processor --> Factory
    Factory --> Interface
    Interface --> Mock
    Interface --> TripoSR
    Processor --> Repo
    Processor --> Storage
    App --> Settings
```

### Package Structure

```
src/modelforge/
├── worker/           # Entry point and application lifecycle
│   ├── main.py       # CLI entry point
│   └── app.py        # App class with signal handling
├── kafka/            # Kafka consumer
│   └── consumer.py   # KafkaConsumerService — polls topic
├── tasks/            # Task orchestration
│   └── processor.py  # TaskProcessor — download → infer → upload → update
├── ml/               # ML inference layer
│   ├── interface.py  # ModelInferenceInterface (ABC)
│   ├── factory.py    # Factory — selects backend by ML_MOCK_MODE
│   ├── mock_service.py    # MockInferenceService (generates cube)
│   └── triposr_service.py # TripoSRService (real inference)
├── database/         # Data access
│   └── repository.py # TaskRepository — PostgreSQL status updates
├── storage/          # Object storage
│   └── s3_service.py # S3StorageService — boto3 wrapper for MinIO
└── config/           # Configuration
    ├── settings.py   # Pydantic BaseSettings (env-driven)
    └── logging.py    # JSON/text logging configuration
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **Strategy pattern for ML** | `ModelInferenceInterface` ABC allows swapping backends without changing orchestration |
| **Factory pattern** | `ML_MOCK_MODE` env var switches between mock and real inference at startup |
| **Constructor injection** | Services injected into `App` and `TaskProcessor` for testability |
| **Pydantic settings** | All config from env vars, validated at startup |
| **Signal handling** | Graceful shutdown on SIGINT/SIGTERM — finishes current task before exit |

## Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.9 |
| ML Framework | PyTorch, TripoSR |
| Message Queue | Apache Kafka (confluent-kafka) |
| Object Storage | MinIO via boto3 (S3-compatible) |
| Database | PostgreSQL (psycopg2) |
| Configuration | pydantic-settings |
| Testing | pytest |
| Container | python:3.9-slim |

## Setup & Installation

### Prerequisites

- Python 3.9+
- Running infrastructure (Kafka, PostgreSQL, MinIO) — see root `make infra`

### Run Locally

```bash
cd ml-service
pip install -r requirements.txt

# Set environment variables (or use deploy/.env)
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export DATABASE_URL=postgresql://modelforge:changeme@localhost:5432/modelforge_db
export S3_ENDPOINT=localhost:9000
export ML_MOCK_MODE=true

PYTHONPATH=src python -m modelforge.worker.main
```

### Run via Docker

```bash
cd deploy
make app   # starts infra + ML Worker
```

## Configuration

All settings are env-var driven via Pydantic `BaseSettings` (see `deploy/.env.example`):

| Variable | Description | Default |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker address | `kafka:9092` |
| `KAFKA_GROUP_ID` | Consumer group ID | `modelforge-ml-worker` |
| `DATABASE_URL` | PostgreSQL connection string | — |
| `S3_ENDPOINT` | MinIO/S3 endpoint | `minio:9000` |
| `S3_ACCESS_KEY` | MinIO access key | — |
| `S3_SECRET_KEY` | MinIO secret key | — |
| `S3_BUCKET_NAME` | Storage bucket | `modelforge` |
| `ML_MOCK_MODE` | Use mock inference (`true`/`false`) | `true` |
| `TRIPSR_DEVICE` | PyTorch device for TripoSR | `cpu` |
| `LOG_FORMAT` | Log format (`json`/`text`) | `json` |

## Testing

### Run All Tests

```bash
cd ml-service
PYTHONPATH=src pytest tests/ -v
```

### Run a Single Test

```bash
cd ml-service
PYTHONPATH=src pytest tests/test_processor.py -v -k "test_name"
```

### Via Makefile (from project root)

```bash
make test-ml
```

## ML Model Integration

The service uses the **Strategy pattern** for ML backends. Two modes are available:

### Mock Mode (`ML_MOCK_MODE=true`, default)

Generates a simple 3D cube. Suitable for testing infrastructure without GPU.

### TripoSR Mode (`ML_MOCK_MODE=false`)

Real 3D model generation from images. Works on both GPU and CPU.

**GPU (faster):**
```bash
pip install -r requirements-gpu.txt   # PyTorch CUDA 11.8
make gpu                               # via Docker
```

**CPU (no GPU needed, slower):**
```bash
pip install -r requirements-cpu.txt   # PyTorch CPU
make cpu-inference                     # via Docker
```

**Shared dependencies** (included in both requirement files):
- TripoSR (`tsr` package from GitHub)
- omegaconf, einops, transformers, huggingface-hub
- rembg (background removal)
- xatlas, moderngl (texture baking)

**Docker images:**
- `Dockerfile` — base (mock only, no torch)
- `Dockerfile.cpu` — CPU inference (`python:3.9-slim` + torch CPU)
- `Dockerfile.gpu` — GPU inference (`nvidia/cuda:11.8.0-runtime`)

HuggingFace model is cached in a Docker volume (`huggingface-cache`) to avoid re-downloading on restart.

### Adding a New ML Backend

1. Implement `ModelInferenceInterface` in a new file under `ml/`
2. Update the factory in `ml/factory.py` to return your implementation
3. Add any new config vars to `config/settings.py`
