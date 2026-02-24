import os
import time
import logging
import json
import psycopg2
import boto3
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from botocore.exceptions import NoCredentialsError, ClientError

# --- Конфигурация ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("modelforge-worker")

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "modelforge.generation.requests")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "modelforge.ml-workers")

DB_URL = os.getenv("DATABASE_URL")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET", "models-output")


# --- Инициализация клиентов ---
def get_db_connection():
    return psycopg2.connect(DB_URL)


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id VARCHAR(255) PRIMARY KEY,
            status VARCHAR(50),
            result_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database initialized.")


def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=f'http://{S3_ENDPOINT}',
        aws_access_key_id=S3_KEY,
        aws_secret_access_key=S3_SECRET,
        config=boto3.session.Config(signature_version='s3v4')
    )


def init_s3_bucket(s3_client):
    """Создает бакет если он не существует"""
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
        logger.info(f"Bucket '{S3_BUCKET}' already exists.")
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            logger.info(f"Creating bucket '{S3_BUCKET}'...")
            s3_client.create_bucket(Bucket=S3_BUCKET)
            logger.info(f"Bucket '{S3_BUCKET}' created successfully.")
        else:
            logger.error(f"Error checking bucket: {e}")
            raise


# --- Логика ---
def update_task_status(task_id, status, result_path=None):
    conn = get_db_connection()
    cur = conn.cursor()
    if result_path:
        cur.execute(
            "UPDATE tasks SET status=%s, result_path=%s, updated_at=CURRENT_TIMESTAMP WHERE task_id=%s",
            (status, result_path, task_id)
        )
    else:
        cur.execute(
            "UPDATE tasks SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE task_id=%s",
            (status, task_id)
        )
    conn.commit()
    cur.close()
    conn.close()


def create_task_in_db(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks (task_id, status) VALUES (%s, %s) ON CONFLICT (task_id) DO NOTHING",
                (task_id, 'PROCESSING'))
    conn.commit()
    cur.close()
    conn.close()


def upload_mock_result(s3_client, task_id):
    """Имитация результата генерации (создает пустой файл .obj)"""
    try:
        file_key = f"{task_id}/result.obj"
        s3_client.put_object(Bucket=S3_BUCKET, Key=file_key, Body=b"v 0.0 0.0 0.0\n")
        logger.info(f"Uploaded mock result to s3://{S3_BUCKET}/{file_key}")
        return f"s3://{S3_BUCKET}/{file_key}"
    except NoCredentialsError:
        logger.error("Credentials not available for S3")
        return None
    except ClientError as e:
        logger.error(f"S3 error: {e}")
        return None


def process_task(task_data, s3_client):
    task_id = task_data.get("task_id")
    logger.info(f"🚀 Starting task {task_id}")

    update_task_status(task_id, 'PROCESSING')
    time.sleep(5)  # Имитация GPU
    result_path = upload_mock_result(s3_client, task_id)

    if result_path:
        update_task_status(task_id, 'COMPLETED', result_path)
        logger.info(f"✅ Task {task_id} completed. Path: {result_path}")
    else:
        update_task_status(task_id, 'FAILED')
        logger.error(f"❌ Task {task_id} failed.")


def main():
    # Инициализация
    init_db()
    s3_client = get_s3_client()
    init_s3_bucket(s3_client)  # <-- Создаем бакет при старте

    # Подключение к Kafka (с повторными попытками)
    consumer = None
    while not consumer:
        try:
            logger.info(f"Trying to connect to Kafka at {KAFKA_SERVERS}...")
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_SERVERS,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            logger.info(f"Connected to Kafka: {TOPIC}")
        except Exception as e:
            logger.error(f"Kafka connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    # Основной цикл обработки
    logger.info(f"Waiting for messages on topic {TOPIC}...")
    try:
        for message in consumer:
            try:
                task_data = message.value
                create_task_in_db(task_data.get("task_id"))
                process_task(task_data, s3_client)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    finally:
        if consumer:
            consumer.close()
            logger.info("Consumer closed.")


if __name__ == "__main__":
    main()