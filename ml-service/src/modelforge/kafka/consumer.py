import json
import time
from typing import Generator, Dict, Any, Optional

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from ..config import Settings
from ..config.logging import get_logger

logger = get_logger(__name__)


class KafkaConsumerService:
    """
    Kafka message consumer service.
    Encapsulates connection and iteration logic.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._consumer: Optional[KafkaConsumer] = None

    def connect(self) -> None:
        """Establish a connection to Kafka with retries."""
        while True:
            try:
                logger.info("Connecting to Kafka at %s...", self.settings.kafka_bootstrap_servers)
                self._consumer = KafkaConsumer(
                    self.settings.kafka_topic,
                    bootstrap_servers=self.settings.kafka_bootstrap_servers,
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    group_id=self.settings.kafka_group_id,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                )
                logger.info("Connected to topic: %s", self.settings.kafka_topic)
                return
            except KafkaError as e:
                logger.error("Kafka connection failed: %s. Retrying in 5s...", e)
                time.sleep(5)

    def consume(self) -> Generator[Dict[str, Any], None, None]:
        """Yield messages from Kafka."""
        if not self._consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")

        logger.info("Waiting for messages on topic %s...", self.settings.kafka_topic)
        for message in self._consumer:
            yield message.value

    def close(self) -> None:
        """Close the Kafka consumer connection."""
        if self._consumer:
            self._consumer.close()
            logger.info("Kafka consumer closed.")
