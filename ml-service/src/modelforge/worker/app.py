import signal
import sys
from typing import Optional

from ..config import Settings
from ..config.logging import get_logger
from ..database.repository import TaskRepository
from ..kafka.consumer import KafkaConsumerService
from ..storage.s3_client import S3StorageService
from ..tasks.processor import TaskProcessor

logger = get_logger(__name__)


class App:
    """
    Основное приложение ModelForge ML Worker.

    Инкапсулирует всю логику инициализации и запуска.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self._running = False

        # Инициализация сервисов (Dependency Injection)
        self.consumer = KafkaConsumerService(self.settings)
        self.repository = TaskRepository(self.settings)
        self.storage = S3StorageService(self.settings)

        # Бизнес-логика
        self.processor = TaskProcessor(
            repository=self.repository,
            storage=self.storage,
            settings=self.settings
        )

        logger.info("App initialized.")

    def _setup_signal_handlers(self):
        """Настраивает обработчики сигналов для graceful shutdown."""

        def signal_handler(sig, frame):
            logger.info("Shutdown signal received. Stopping gracefully...")
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self) -> None:
        """Запускает основной цикл обработки задач."""
        self._running = True
        self._setup_signal_handlers()

        logger.info("Starting ModelForge ML Worker...")
        self.consumer.connect()

        try:
            for task_data in self.consumer.consume():
                if not self._running:
                    break
                self.repository.create(task_data.get("task_id"), 'PENDING')
                self.processor.process(task_data)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received.")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Корректное завершение работы."""
        logger.info("Shutting down...")
        self.consumer.close()
        logger.info("Worker stopped.")


def create_app(settings: Optional[Settings] = None) -> App:
    """Factory function для создания приложения (удобно для тестов)."""
    return App(settings=settings)
