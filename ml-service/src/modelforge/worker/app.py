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
    ModelForge ML Worker application.

    Encapsulates initialization, signal handling, and the main processing loop.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self._running = False

        # Service initialization (Dependency Injection)
        self.consumer = KafkaConsumerService(self.settings)
        self.repository = TaskRepository(self.settings)
        self.storage = S3StorageService(self.settings)

        # Business logic
        self.processor = TaskProcessor(
            repository=self.repository,
            storage=self.storage,
            settings=self.settings,
        )

        logger.info("App initialized.")

    def _setup_signal_handlers(self):
        """Configure signal handlers for graceful shutdown."""

        def signal_handler(sig, frame):
            logger.info("Shutdown signal received. Stopping gracefully...")
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self) -> None:
        """Start the main task-processing loop."""
        self._running = True
        self._setup_signal_handlers()

        logger.info("Starting ModelForge ML Worker...")
        self.consumer.connect()

        try:
            for task_data in self.consumer.consume():
                if not self._running:
                    break
                # Support both snake_case (legacy) and camelCase (Kotlin service) formats
                task_id = task_data.get("task_id") or task_data.get("taskId", "unknown")
                normalized = self._normalize_task(task_data, task_id)
                self.repository.create(task_id, "PENDING")
                self.processor.process(normalized)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received.")
        except Exception as e:
            logger.error("Fatal error: %s", e, exc_info=True)
            sys.exit(1)
        finally:
            self.shutdown()

    @staticmethod
    def _normalize_task(task_data: dict, task_id: str) -> dict:
        """Normalize task message from Kotlin service (camelCase) to ML worker format (snake_case)."""
        if "input" in task_data and "s3_path" in task_data.get("input", {}):
            return task_data  # Already in expected format

        s3_path = task_data.get("s3InputKey") or task_data.get("s3_input_key", "")
        return {
            "task_id": task_id,
            "input": {"s3_path": s3_path},
            "params": {"output_format": "glb"},
        }

    def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down...")
        self.consumer.close()
        logger.info("Worker stopped.")


def create_app(settings: Optional[Settings] = None) -> App:
    """Factory function for creating the application (convenient for tests)."""
    return App(settings=settings)
