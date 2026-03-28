import io
import time
from typing import Dict, Any

import trimesh
from PIL import Image

from .inference_interface import ModelInferenceInterface, ModelInferenceResult
from ..config.logging import get_logger

logger = get_logger(__name__)


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

        # Assign vertex colors for visual appeal in GLB viewer
        mesh.visual.vertex_colors = [100, 149, 237, 255]  # Cornflower blue

        # Экспортируем в GLB (binary glTF) — supported by model-viewer
        with io.BytesIO() as f:
            mesh.export(f, file_type='glb')
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
