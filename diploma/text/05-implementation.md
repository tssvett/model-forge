# Программная реализация платформы

<!--
Цель главы: показать что архитектурные решения из главы 3 воплощены в коде.
Объём: 10-12 страниц (~3000-3500 слов).
ИСТОЧНИК: реальный код в D:/model-forge/{frontend, kotlin-service, ml-service, deploy}.
Ссылаться на конкретные файлы (например, ml-service/src/modelforge/ml/triposr_inference.py).
-->

## Frontend: React-приложение

<!--
Объём: 1.5-2 страницы.
- Стек: React + TypeScript + Vite.
- Структура каталогов (компоненты, хуки, API-клиент).
- Ключевые компоненты: загрузка изображения, превью, прогресс-бар, 3D-просмотрщик результата.
- Polling/SSE для отслеживания статуса задачи.
- Ссылки на файлы (например, frontend/src/components/UploadView.tsx).

Рисунок 4 – Скриншот пользовательского интерфейса.
-->

## Kotlin Backend: Spring Boot REST API

<!--
Объём: 3-4 страницы.

### Структура проекта
- Слои: controller → service → repository.
- DTO vs entity.
- DI через Spring.

### REST API
- Endpoints (POST /tasks, GET /tasks/{id}, GET /tasks).
- OpenAPI спецификация — автогенерация из контроллеров.
- Валидация входных данных (Bean Validation).

Таблица 4 – Перечень REST-эндпоинтов.

### Persistence слой
- JPA + Hibernate.
- Liquibase changelogs для миграций.
- PostgreSQL connection pool (HikariCP).

### Интеграция с Kafka
- Producer для отправки задач в topic.
- Consumer для приёма результатов.
- Обработка ошибок и retry-логика.

### Интеграция с MinIO
- S3-клиент (AWS SDK или MinIO native).
- Presigned URLs для загрузки/скачивания напрямую от клиента.

Ссылки на файлы: kotlin-service/src/main/kotlin/...
-->

## ML Worker: Python + FastAPI

<!--
Объём: 3 страницы.

### Архитектура воркера
- Асинхронный Kafka-консьюмер (aiokafka).
- Загрузка модели TripoSR при старте (warm cache).
- Ленивая инициализация на первом запросе.

### Инференс
- Препроцессинг входного изображения.
- TripoSR inference (вызов модели).
- Постпроцессинг (генерация .obj/.glb).

### Mock-режим
- Для разработки без GPU и тестов.
- Возвращает фиктивную 3D-модель.

### Управление весами модели
- Weight manager: загрузка чекпоинтов из локального кэша или MinIO.
- Версионирование моделей.

Ссылки: ml-service/src/modelforge/ml/triposr_inference.py, weight_manager.py.

Рисунок 4 – Диаграмма работы ML-воркера.
-->

## Развёртывание

<!--
Объём: 1.5 страницы.

### Контейнеризация
- Dockerfile'ы для каждого сервиса.
- Multi-stage builds для уменьшения размера.

### Локальное развёртывание
- docker-compose.yml: все сервисы + инфраструктура (Postgres, MinIO, Kafka, Loki, Grafana).
- Команды make для типичных операций.

### Готовность к продакшен-развёртыванию
- Helm-чарты или Kubernetes-манифесты (опционально).
- Подготовка к CI/CD.

Ссылки: deploy/, Makefile.
-->

## Логирование и мониторинг

<!--
Объём: 1 страница.

### Логирование
- Loki как агрегатор.
- Структурированные JSON-логи во всех сервисах.
- Correlation ID для трассировки запроса через сервисы.

### Мониторинг
- Grafana дашборды.
- Метрики: количество задач, success rate, времена инференса.
- (Опционально) Prometheus.

Рисунок 4 – Скриншот Grafana-дашборда.
-->

<!--
ИСТОЧНИКИ для главы 5:
- Spring Boot документация
- FastAPI документация
- Docker документация
- aiokafka, kafka-python документация
- Loki/Grafana документация
-->
