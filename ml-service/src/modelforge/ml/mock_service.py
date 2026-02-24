import logging
import io
import time
import trimesh
import numpy as np
from PIL import Image
from typing import Dict, Any

from .inference_interface import ModelInferenceInterface, ModelInferenceResult

logger = logging.getLogger(__name__)


class MockInferenceService(ModelInferenceInterface):
    """
    Mock-реализация для тестов и разработки.

    Имитирует работу модели: спит, генерирует простой куб и фейковые метрики.
    Позволяет тестировать всю инфраструктуру без реальной ML-модели.
    """

    def __init__(self, processing_delay: float = 5.0):
        self.processing_delay = processing_delay
        logger.info("MockInferenceService initialized (Delay: %ss)", processing_delay)

    def is_available(self) -> bool:
        return True

    def infer(self, image: Image.Image, params: Dict[str, Any]) -> ModelInferenceResult:
        logger.info(f"🎭 [MOCK] Starting inference for image size {image.size}...")

        # 1. Имитация тяжелого вычисления
        time.sleep(self.processing_delay)

        # 2. Генерация простого 3D объекта (Куб) вместо сложной модели
        mesh = trimesh.creation.box(extents=[1, 1, 1])

        # Экспортируем в байты (как будет делать реальная модель)
        with io.BytesIO() as f:
            mesh.export(f, file_type='obj')
            mesh_bytes = f.getvalue()

        # 3. Генерация фейковой текстуры (серый квадрат)
        texture_img = Image.new('RGB', (512, 512), color='gray')
        with io.BytesIO() as f:
            texture_img.save(f, format='PNG')
            texture_bytes = f.getvalue()

        # 4. Фейковые научные метрики для диплома
        fake_metrics = {
            "chamfer_distance": 0.042,
            "iou_3d": 0.89,
            "inference_time_sec": self.processing_delay,
            "device_used": "mock_cpu",
            "mock_mode": True
        }

        logger.info("🎭 [MOCK] Inference completed successfully.")

        return ModelInferenceResult(
            success=True,
            mesh_bytes=mesh_bytes,
            texture_bytes=texture_bytes,
            metrics=fake_metrics
        )
