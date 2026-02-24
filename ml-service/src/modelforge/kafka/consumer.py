import logging
import json
import time
from typing import Generator, Dict, Any, Optional
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from ..config import Settings

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """
    Сервис для потребления сообщений из Kafka.
    Инкапсулирует логику подключения и итерации.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._consumer: Optional[KafkaConsumer] = None

    def connect(self) -> None:
        """Устанавливает соединение с Kafka с повторными попытками."""
        while True:
            try:
                logger.info(f"Connecting to Kafka at {self.settings.kafka_bootstrap_servers}...")
                self._consumer = KafkaConsumer(
                    self.settings.kafka_topic,
                    bootstrap_servers=self.settings.kafka_bootstrap_servers,
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    group_id=self.settings.kafka_group_id,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
                )
                logger.info(f"Successfully connected to topic: {self.settings.kafka_topic}")
                return
            except KafkaError as e:
                logger.error(f"Kafka connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def consume(self) -> Generator[Dict[str, Any], None, None]:
        """Генератор сообщений из Kafka."""
        if not self._consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")

        logger.info(f"Waiting for messages on topic {self.settings.kafka_topic}...")
        for message in self._consumer:
            yield message.value

    def close(self) -> None:
        """Закрывает соединение с Kafka."""
        if self._consumer:
            self._consumer.close()
            logger.info("Kafka consumer closed.")
