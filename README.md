# ModelForge

Микросервисная платформа для генерации 3D-моделей из изображений.

## Архитектура

```
Browser (React SPA)
  │  HTTP / JWT
  ▼
Nginx (:80) → Kotlin Service (:8080)
                  ├─ PostgreSQL (:5432)
                  ├─ MinIO (:9000)
                  └─ Kafka (:9092)
                        │
                        ▼
                  ML Worker (TripoSR / Mock)
                        ├─ PostgreSQL  — обновление статуса
                        └─ MinIO       — загрузка результатов

Logging: Promtail → Loki → Grafana (:3000)
```

| Компонент | Технология | Порт |
|-----------|-----------|------|
| Frontend | React 18 + Vite + Nginx | 80 |
| Kotlin Service | Spring Boot 3.2, Kotlin 1.9 | 8080 |
| ML Worker | Python 3.9, TripoSR | — |
| PostgreSQL | 15-alpine | 5432 |
| Kafka | Confluent 7.5.0 | 9092 |
| MinIO | latest | 9000 / 9001 (console) |
| Grafana | latest | 3000 |

## Быстрый старт

```bash
# 1. Клонировать и настроить переменные окружения
git clone <repo-url> && cd model-forge
make init              # создаёт deploy/.env из .env.example

# 2. Запустить полный стек
make full              # все сервисы + логирование

# 3. Открыть в браузере
#    Frontend:      http://localhost
#    Swagger API:   http://localhost:8080/swagger-ui.html
#    MinIO Console: http://localhost:9001  (modelforge_admin / changeme)
#    Grafana:       http://localhost:3000  (admin / changeme)
```

## Команды (Makefile)

```bash
make help              # справка по всем командам
```

### Запуск

| Команда | Что запускает |
|---------|--------------|
| `make infra` | Kafka, PostgreSQL, MinIO, Zookeeper |
| `make app` | Инфраструктура + ML Worker |
| `make backend` | Инфраструктура + Kotlin API + ML Worker |
| `make full` | Все сервисы + логирование (Loki/Grafana) |
| `make gpu` | Полный стек с NVIDIA GPU для ML Worker |
| `make dev` | Инфраструктура + логирование (сервисы локально) |

### Остановка

| Команда | Действие |
|---------|----------|
| `make down` | Остановить контейнеры (данные сохраняются) |
| `make clean` | Остановить + удалить тома (данные потеряны) |

### Тестирование

| Команда | Что тестирует |
|---------|--------------|
| `make test` | Все тесты (ML + Kotlin + Frontend) |
| `make test-ml` | `pytest` для ML Service |
| `make test-kotlin` | `./gradlew check` для Kotlin Service |
| `make test-frontend` | `npm run build` для Frontend |

### Логи и утилиты

```bash
make logs              # все логи (follow)
make logs-ml           # логи ML Worker
make logs-kotlin       # логи Kotlin Service
make ps                # статус контейнеров
make seed              # загрузить тестовые данные
make build             # собрать Docker-образы
```

## Интеграция ML-модели (TripoSR)

ML Worker поддерживает два режима работы через переменную `ML_MOCK_MODE`:

- **Mock** (`ML_MOCK_MODE=true`, по умолчанию) — генерирует куб, подходит для тестирования инфраструктуры.
- **TripoSR** (`ML_MOCK_MODE=false`) — реальная генерация 3D-модели из изображения.

### Запуск с реальной моделью (GPU)

```bash
# 1. Убедитесь, что установлены: NVIDIA Driver, nvidia-container-toolkit
# 2. В deploy/.env:
#    ML_MOCK_MODE=false
#    TRIPSR_DEVICE=cuda:0

make gpu
```

### Зависимости TripoSR

Базовые зависимости ML Worker — `ml-service/requirements.txt`.
Для работы с GPU и TripoSR — дополнительно `ml-service/requirements-gpu.txt`:
- PyTorch (CUDA 11.8)
- omegaconf, einops, transformers, huggingface-hub
- rembg (удаление фона)
- xatlas, moderngl (запечка текстур)

## Структура проекта

```
model-forge/
├── frontend/              # React SPA (Vite)
├── kotlin-service/        # Spring Boot REST API
├── ml-service/            # Python ML Worker
│   ├── src/modelforge/
│   │   ├── ml/            # Инференс (TripoSR / Mock)
│   │   ├── kafka/         # Kafka consumer
│   │   ├── tasks/         # Обработка задач
│   │   ├── database/      # PostgreSQL repository
│   │   ├── storage/       # S3/MinIO клиент
│   │   └── config/        # Pydantic settings
│   ├── requirements.txt
│   └── requirements-gpu.txt
├── deploy/                # Docker Compose конфигурации
│   ├── docker-compose.yml          # networks, volumes
│   ├── docker-compose.infra.yml    # Kafka, PG, MinIO, ZK
│   ├── docker-compose.app.yml      # ML Worker
│   ├── docker-compose.kotlin.yml   # Kotlin Service
│   ├── docker-compose.frontend.yml # Frontend
│   ├── docker-compose.logging.yml  # Loki, Promtail, Grafana
│   ├── docker-compose.gpu.yml      # GPU overlay для ML Worker
│   └── .env.example
├── logging/               # Promtail / Grafana provisioning
├── Makefile               # Команды запуска
└── CLAUDE.md              # Инструкции для Claude Code
```

## CI/CD

GitHub Actions пайплайны (`.github/workflows/`):

| Пайплайн | Триггер | Шаги |
|-----------|---------|------|
| `frontend-ci.yml` | `frontend/**` | npm ci → build → Docker build |
| `kotlin-service-ci.yml` | `kotlin-service/**` | Gradle build → integration tests → Docker build |
| `ml-service-ci.yml` | `ml-service/**` | pip install → pytest → Docker build |

## UI-ссылки (при `make full`)

| Сервис | URL | Логин |
|--------|-----|-------|
| Frontend | http://localhost | — |
| Swagger API | http://localhost:8080/swagger-ui.html | JWT |
| MinIO Console | http://localhost:9001 | `modelforge_admin` / `changeme` |
| Grafana | http://localhost:3000 | `admin` / `changeme` |
