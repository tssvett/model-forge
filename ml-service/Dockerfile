FROM python:3.9-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходный код
COPY src/ ./src/
COPY scripts/ ./scripts/

# Оптимизация Python и логирования
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TORCH_NUM_THREADS=1

CMD ["python", "-m", "modelforge.worker.main"]