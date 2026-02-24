import json
import time
import uuid
from kafka import KafkaProducer

# Для локального запуска с хост-машины
BOOTSTRAP_SERVERS = ['localhost:9094']
TOPIC_NAME = 'modelforge.generation.requests'


def main():
    print(f"Connecting to Kafka at {BOOTSTRAP_SERVERS}...")
    try:
        producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("Connected! Sending 5 test tasks...")

        for i in range(5):
            task = {
                "task_id": str(uuid.uuid4()),
                "image_path": f"s3://input/photo_{i}.jpg",
                "user_id": 123
            }
            future = producer.send(TOPIC_NAME, value=task)
            record_metadata = future.get(timeout=10)
            print(f"✅ Sent task {task['task_id']}")
            time.sleep(1)

        producer.flush()
        producer.close()
        print("Done.")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()