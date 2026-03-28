import io
import json
from typing import Dict, Any

from PIL import Image

from ..config import Settings
from ..config.logging import get_logger
from ..database.repository import TaskRepository
from ..ml.factory import create_inference_service
from ..ml.inference_interface import ModelInferenceInterface
from ..storage.s3_client import S3StorageService

logger = get_logger(__name__)


class TaskProcessor:
    """
    Бизнес-логика обработки задач генерации 3D-моделей.

    Не зависит от конкретной ML-модели напрямую (Dependency Injection + Interface).
    """

    def __init__(
            self,
            repository: TaskRepository,
            storage: S3StorageService,
            settings: Settings
    ):
        self.repository = repository
        self.storage = storage
        self.settings = settings

        # 🔥 КЛЮЧЕВОЙ МОМЕНТ: Создаем сервис через фабрику
        # В переменной ml_service будет либо Mock, либо TripoSR (когда будет готов)
        self.ml_service: ModelInferenceInterface = create_inference_service(settings)

        # Проверяем доступность при старте
        if not self.ml_service.is_available():
            logger.error("ML Service failed to initialize!")

    def process(self, task_data: Dict[str, Any]) -> bool:
        """
        Обрабатывает задачу генерации.

        :param task_data: Данные задачи из Kafka
        :return: True если успешно, False иначе
        """
        task_id = task_data.get("task_id", "unknown")
        input_config = task_data.get("input", {})
        params = task_data.get("params", {})

        input_s3_path = input_config.get("s3_path")
        output_format = params.get("output_format", "glb")

        logger.info(f"🚀 Starting task {task_id} for {input_s3_path}")

        try:
            # 1. Обновляем статус
            self.repository.update_status(task_id, 'PROCESSING')

            # 2. Скачиваем входное изображение из S3
            logger.info(f"📥 Downloading image from {input_s3_path}")
            image_bytes = self.storage.download_file(input_s3_path)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # 3. Запускаем инференс (через интерфейс!)
            # Processor не знает, что внутри: сон или GPU
            logger.info("🧠 Running ML inference...")
            result = self.ml_service.infer(image, params)

            if not result.success:
                raise RuntimeError(f"ML Inference failed: {result.error}")

            # 4. Загружаем результаты в S3
            mesh_key = f"results/{task_id}/model.{output_format}"
            texture_key = f"results/{task_id}/texture.png"

            mesh_url = self.storage.upload_bytes(mesh_key, result.mesh_bytes)

            texture_url = None
            if result.texture_bytes:
                texture_url = self.storage.upload_bytes(texture_key, result.texture_bytes)

            # 5. Подготавливаем метаданные для БД
            db_result = {
                "model_url": mesh_url,
                "texture_url": texture_url,
                "output_format": output_format,
                "metrics": result.metrics
            }

            # 6. Обновляем статус + сохраняем результат (s3_output_key = mesh S3 key)
            self.repository.update_status(task_id, 'COMPLETED', mesh_key)

            logger.info(f"✅ Task {task_id} completed. Model: {mesh_url}")
            return True

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            self.repository.update_status(task_id, 'FAILED')
            return False
