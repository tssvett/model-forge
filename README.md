# ModelForge

Микросервисная система генерации 3D-моделей на основе методов компьютерного зрения.

## Запуск

Все команды выполняются из директории `deploy/`.

### Предварительная настройка
```bash
cd deploy
cp .env.example .env
# При необходимости отредактируйте переменные в .env
```

### Запуск с логированием (Loki + Grafana)
```bash
docker-compose -f docker-compose.yml -f docker-compose.infra.yml -f docker-compose.logging.yml -f docker-compose.app.yml up -d --build
```

### Запуск без логирования (инфраструктура + приложение)
```bash
docker-compose -f docker-compose.yml -f docker-compose.infra.yml -f docker-compose.app.yml up -d --build
```

### Запуск только инфраструктуры
```bash
docker-compose -f docker-compose.yml -f docker-compose.infra.yml up -d
```

## Просмотр логов

### Через Docker Compose
```bash
# Логи конкретного сервиса
docker-compose logs -f ml-worker
docker-compose logs -f kafka

# Все логи
docker-compose logs -f
```

### Через Grafana (если запущен стек логирования)
1. Откройте http://localhost:3000
2. Авторизуйтесь (admin/admin)
3. Перейдите в Explore → выберите DataSource Loki
4. Пример запроса: `{service="modelforge-ml-worker"}`

## Остановка

```bash
# Остановка с сохранением данных
docker-compose -f docker-compose.yml -f docker-compose.infra.yml -f docker-compose.logging.yml -f docker-compose.app.yml down

# Остановка с удалением томов (данные будут потеряны)
docker-compose -f docker-compose.yml -f docker-compose.infra.yml -f docker-compose.logging.yml -f docker-compose.app.yml down -v
```

> Примечание: при выполнении `down` указывайте те же файлы `-f`, которые использовались при запуске.