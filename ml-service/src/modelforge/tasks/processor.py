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
    Task processing pipeline for 3D model generation.

    Decoupled from the concrete ML backend via Dependency Injection + Interface.
    Before each task, runtime settings are read from the database so that
    mock_mode and device can be toggled without restarting the worker.
    """

    def __init__(
        self,
        repository: TaskRepository,
        storage: S3StorageService,
        settings: Settings,
    ):
        self.repository = repository
        self.storage = storage
        self.settings = settings

        # Build the initial inference service from env-based settings
        self.ml_service: ModelInferenceInterface = create_inference_service(settings)
        self._active_mock_mode: bool = settings.ml_mock_mode
        self._active_device: str = settings.tripsr_device

        if not self.ml_service.is_available():
            logger.error("ML service failed to initialize!")

    # ------------------------------------------------------------------
    # Runtime settings hot-reload
    # ------------------------------------------------------------------

    def _maybe_reload_service(self) -> None:
        """Check app_settings in DB; rebuild ML service if config changed."""
        runtime = self.repository.get_app_settings()
        if not runtime:
            return

        new_mock = runtime.get("ml_mock_mode", str(self._active_mock_mode)).lower() == "true"
        new_device = runtime.get("ml_device", self._active_device)

        if new_mock == self._active_mock_mode and new_device == self._active_device:
            return

        logger.info(
            "Runtime settings changed: mock_mode=%s->%s, device=%s->%s. Rebuilding ML service...",
            self._active_mock_mode, new_mock, self._active_device, new_device,
        )

        self.settings.ml_mock_mode = new_mock
        self.settings.tripsr_device = new_device
        self.ml_service = create_inference_service(self.settings)
        self._active_mock_mode = new_mock
        self._active_device = new_device

    # ------------------------------------------------------------------
    # Main processing pipeline
    # ------------------------------------------------------------------

    def process(self, task_data: Dict[str, Any]) -> bool:
        """
        Process a single generation task.

        :param task_data: Task payload from Kafka
        :return: True on success, False on failure
        """
        task_id = task_data.get("task_id", "unknown")
        input_config = task_data.get("input", {})
        params = task_data.get("params", {})

        input_s3_path = input_config.get("s3_path")
        output_format = params.get("output_format", "glb")

        logger.info("Starting task %s for %s", task_id, input_s3_path)

        try:
            # 0. Hot-reload ML service if settings changed in DB
            self._maybe_reload_service()

            # 1. Update status
            self.repository.update_status(task_id, "PROCESSING")

            # 2. Download input image from S3
            logger.info("Downloading image from %s", input_s3_path)
            image_bytes = self.storage.download_file(input_s3_path)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # 3. Run inference (mock or real — transparent via interface)
            logger.info("Running ML inference...")
            result = self.ml_service.infer(image, params)

            if not result.success:
                raise RuntimeError(f"ML inference failed: {result.error}")

            # 4. Upload results to S3
            mesh_key = f"results/{task_id}/model.{output_format}"
            texture_key = f"results/{task_id}/texture.png"

            mesh_url = self.storage.upload_bytes(mesh_key, result.mesh_bytes)

            texture_url = None
            if result.texture_bytes:
                texture_url = self.storage.upload_bytes(texture_key, result.texture_bytes)

            # 5. Build result metadata
            db_result = {
                "model_url": mesh_url,
                "texture_url": texture_url,
                "output_format": output_format,
                "metrics": result.metrics,
            }

            # 6. Mark task completed (s3_output_key = mesh S3 key)
            self.repository.update_status(task_id, "COMPLETED", mesh_key)

            logger.info("Task %s completed. Model: %s", task_id, mesh_url)
            return True

        except Exception as e:
            logger.error("Error processing task %s: %s", task_id, e, exc_info=True)
            self.repository.update_status(task_id, "FAILED")
            return False
