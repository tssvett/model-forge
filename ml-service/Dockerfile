FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей (нужны для компиляции psycopg2)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода сервиса
COPY . .

# Точка входа
CMD ["python", "main.py"]
