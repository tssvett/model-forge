# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ModelForge is a platform for generating 3D models from images. It consists of three components:

1. **Kotlin Service** (`kotlin-service/`) — Spring Boot REST API gateway. Handles user authentication (JWT), task management, file uploads to MinIO, and publishes events to Kafka via the transactional outbox pattern. See `kotlin-service/README.md` for full documentation.

2. **ML Service** (`ml-service/`) — Python worker that consumes tasks from Kafka, downloads images from MinIO (S3-compatible), runs ML inference, and uploads results back to MinIO, tracking status in PostgreSQL.

3. **Frontend** (`frontend/`) — React SPA built with Vite. Provides user authentication, task creation with image upload, real-time task tracking via polling, and 3D model download. See `frontend/README.md` for full documentation.

## Build & Run Commands

### Full stack (Makefile — from project root)
```bash
make init              # creates deploy/.env from .env.example (first time)
make full              # all services + logging + monitoring
make down              # stop containers (data preserved)
make clean             # stop + remove volumes
```

### Selective start
```bash
make infra             # Kafka, PostgreSQL, MinIO, Zookeeper
make app               # infra + ML Worker
make backend           # infra + Kotlin API + ML Worker
make gpu               # full stack with NVIDIA GPU for ML Worker
make cpu-inference     # full stack with real TripoSR on CPU (no GPU needed)
make monitoring        # infra + logging + monitoring (Prometheus)
make dev               # infra + logging + monitoring (run services locally)
```

### Logs & utilities
```bash
make logs              # tail all service logs
make logs-ml           # tail ML Worker logs
make logs-kotlin       # tail Kotlin Service logs
make logs-kafka        # tail Kafka logs
make build             # build all Docker images (no start)
make build-ml          # build ML Service image
make build-kotlin      # build Kotlin Service image
make build-frontend    # build Frontend image
make ps                # show container status
make help              # show all available targets
```

### Direct docker-compose (from `deploy/` directory)

The `deploy/` directory contains 9 compose files: `docker-compose.yml` (networks/volumes), `infra.yml` (Kafka, PG, MinIO, ZK), `app.yml` (ML Worker), `kotlin.yml` (Kotlin API), `frontend.yml` (React SPA), `logging.yml` (Loki/Grafana/Promtail), `monitoring.yml` (Prometheus/postgres-exporter), `gpu.yml` (NVIDIA GPU overlay), `cpu-inference.yml` (CPU inference overlay).

```bash
cp .env.example .env  # first time only
docker-compose -f docker-compose.yml -f docker-compose.infra.yml -f docker-compose.logging.yml -f docker-compose.app.yml up -d --build
```

### Run ML service tests
```bash
cd ml-service
PYTHONPATH=src pytest tests/ -v
```

### Run a single ML service test
```bash
cd ml-service
PYTHONPATH=src pytest tests/test_processor.py -v -k "test_name"
```

### Run Kotlin service tests
```bash
cd kotlin-service
./gradlew test              # unit tests
./gradlew integrationTest   # integration tests
./gradlew check             # all tests
```

### Run all tests via Makefile
```bash
make test              # all tests (ML + Kotlin + Frontend)
make test-ml           # pytest for ML Service
make test-kotlin       # ./gradlew check for Kotlin Service
make test-frontend     # npm run build for Frontend
```

### Seed test data (requires running infrastructure)
```bash
make seed              # or manually:
python ml-service/scripts/seed_minio.py   # uploads test images to MinIO
python ml-service/scripts/seed_tasks.py   # sends test tasks to Kafka
```

## Architecture

The system is a distributed pipeline:

**Client** → **Kotlin Service** (REST API + auth) → **Kafka** (task queue) → **ML Worker** (processing) → **MinIO** (artifact storage), with **PostgreSQL** for task state tracking, **Loki/Grafana/Promtail** for logging, and **Prometheus/Grafana** for metrics monitoring.

### Kotlin Service (`kotlin-service/`)

Layered Spring Boot architecture: Controllers → Services → Repositories (JdbcTemplate). Key patterns: transactional outbox for Kafka, JWT stateless auth, Liquibase migrations. Exposes Prometheus metrics via Micrometer (`/actuator/prometheus`). Full details in `kotlin-service/README.md`.

### Frontend (`frontend/`)

React 18 SPA built with Vite. CSS Modules for styling, React Router for navigation, Axios with JWT interceptors for API calls. Includes a 3D model viewer (`@google/model-viewer`) for previewing generated GLB files. Key components: `AuthContext` for auth state, `ProtectedRoute` for route guards, `ModelViewer` for 3D previews. See `frontend/README.md` for full documentation.

### ML Service (`ml-service/`)

All application code lives in `ml-service/src/modelforge/` with these layers:

- **worker/** — Entry point (`main.py`) and application lifecycle (`app.py`) with signal handling
- **kafka/** — `KafkaConsumerService` polls `modelforge.generation.requests` topic
- **tasks/** — `TaskProcessor` orchestrates the pipeline: download image → run inference → upload results → update status
- **ml/** — ML inference behind `ModelInferenceInterface` ABC. `MockInferenceService` for dev/test, real implementations (e.g. TripoSR) to be added via `factory.py`
- **database/** — `TaskRepository` for PostgreSQL task state (PENDING → COMPLETED/FAILED)
- **storage/** — `S3StorageService` wraps boto3 for MinIO operations
- **config/** — Pydantic `BaseSettings` for env-based configuration; JSON/text logging setup
- **metrics/** — Prometheus metrics (`prometheus-client`): task counters, duration histograms, S3/inference timing. Exposes `/metrics` on port 8000

TripoSR inference can run on GPU or CPU. Single unified `Dockerfile` with `ARG MODE=mock|cpu|gpu` — build via `docker build --build-arg MODE=cpu .` or use `make gpu` / `make cpu-inference`. TripoSR is git-cloned into `/opt/triposr` (no setup.py). HuggingFace model weights are cached in a persistent volume (`HF_HOME`), not baked into the image.

## Key Patterns

- **Factory pattern** in `ml/factory.py` — switches ML backend based on `ML_MOCK_MODE` env var
- **Strategy pattern** — `ModelInferenceInterface` allows swapping ML implementations
- **Constructor injection** — services are injected into `App` and `TaskProcessor`
- Configuration is entirely env-var driven via pydantic-settings (see `deploy/.env.example` for all variables)

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

- `frontend-ci.yml` — triggers on `frontend/**` changes: npm ci → build → Docker build
- `kotlin-service-ci.yml` — triggers on `kotlin-service/**` changes: Gradle build → integration tests → Docker build
- `ml-service-ci.yml` — triggers on `ml-service/**` changes: pip install → pytest → Docker build

## Token Economy — MANDATORY ⚠️ КРИТИЧЕСКИ ВАЖНО

You MUST minimize context window consumption. This is not optional. **EVERY token counts.** Past sessions wasted tokens massively (73+ Bash calls, 58+ Read calls per session). This MUST NOT repeat.

### Rules

1. **NEVER use Bash for commands producing >20 lines of output.** Use `ctx_batch_execute` instead — it indexes results in FTS5 and returns only a summary. Bash is ONLY for: git writes, mkdir, rm, mv, navigation, and short-output commands.
2. **NEVER use Read for analysis/exploration.** Use `ctx_execute_file(path, language, code)` instead. Use Read ONLY when you plan to Edit the file immediately after.
3. **Use `ctx_batch_execute`** for all git, gh, docker, and system commands. ONE call replaces many individual Bash calls.
4. **Use `ctx_search`** for follow-up queries instead of re-running commands or re-reading files.
5. **CI polling:** Write a single script via `ctx_execute` that checks and summarizes CI status, instead of multiple raw `gh` calls.
6. **NEVER read the same file twice.** If you already read it, use `ctx_search` to recall what you need.
7. **Agent subagent results** are returned to context — keep them focused and concise by writing precise prompts.
8. **NEVER use WebFetch.** Use `ctx_fetch_and_index` instead.

### Tool Selection Priority

| Task | Use | NOT |
|------|-----|-----|
| Run commands, check status | `ctx_batch_execute` | Bash |
| Analyze/explore files | `ctx_execute_file` | Read |
| Follow-up questions | `ctx_search` | Re-run commands |
| Fetch URLs | `ctx_fetch_and_index` | WebFetch |
| Edit files | Read → Edit | (Read is OK here) |

## Workflow Tools — MANDATORY

### Beads (Issue Tracking)
Beads is initialized in this project. Use it for multi-session task tracking:
- **Start of session:** Run `/beads:ready` to find tasks to work on
- **During work:** Update issue status, add comments via `/beads:comments`
- **Creating tasks:** Use `/beads:beads` for issue CRUD
- **Before finishing:** Log work via `/beads:audit`

### Template Bridge
Use `/template-bridge:unified-workflow` at the start of development sessions. This combines Superpowers + Beads + Templates for structured development:
- **Before coding:** Check for relevant templates via `/template-bridge:browse-templates`
- **Feature work:** Use `/feature-dev:feature-dev` for guided development
- **Plans:** Use `/superpowers:writing-plans` before multi-step tasks

### Context-Mode
Always verify context-mode is active. Use `/ctx-stats` to check savings. Target: **>70% context savings** per session.

## Language & Runtime

- **Kotlin Service:** Kotlin 1.9.22, Spring Boot 3.2.2, JDK 17, Gradle 8.5
- **ML Service:** Python 3.9, dependencies in `ml-service/requirements.txt` (base), `requirements-cpu.txt` (CPU inference), `requirements-gpu.txt` (GPU inference). Single unified Dockerfile with `ARG MODE=mock|cpu|gpu`. Docker images: `python:3.9-slim` (mock/cpu), `nvidia/cuda:11.8.0-runtime` (GPU)
- **Frontend:** React 18.3.1, Vite 5.3.1, React Router 6.23.1, Node 18+
- Commit messages are in Russian


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
