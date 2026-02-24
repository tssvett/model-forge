#!/usr/bin/env python3
"""
Скрипт для отправки тестовых задач в Kafka.
Запускается отдельно от основного сервиса.

Контракт сообщения:
{
  "task_id": "uuid",
  "input": { "s3_path": "s3://bucket/key" },
  "params": { "output_format": "obj", ... }
}
"""

import sys
import os
import json
import time
import uuid

# Добавляем src в path для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kafka import KafkaProducer
from modelforge.config import Settings

settings = Settings()


def main():
    print(f"📤 Connecting to Kafka at {settings.kafka_bootstrap_servers}...")

    # Для запуска с хост-машины используем localhost:9094
    bootstrap_servers = ['localhost:9094']

    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("✅ Connected! Sending test tasks...")

        for i in range(5):
            task = {
                "task_id": str(uuid.uuid4()),
                "input": {
                    "s3_path": f"s3://models-output/test/photo_{i}.jpg",
                    "format": "jpg"
                },
                "params": {
                    "remove_background": True,
                    "output_format": "obj",
                    "collect_metrics": True
                }
            }

            future = producer.send(settings.kafka_topic, value=task)
            record_metadata = future.get(timeout=10)

            print(f"✅ Sent task {task['task_id']} to partition {record_metadata.partition}")
            time.sleep(1)

        producer.flush()
        producer.close()
        print("🎉 Done.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
