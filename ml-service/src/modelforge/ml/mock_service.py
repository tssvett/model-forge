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
    Mock implementation for testing and development.

    Simulates model work: sleeps, generates a simple cube, and returns
    fake metrics. Useful for testing the full infrastructure without a real model.
    """

    def __init__(self, processing_delay: float = 5.0):
        self.processing_delay = processing_delay
        logger.info("MockInferenceService initialized (delay: %ss)", processing_delay)

    def is_available(self) -> bool:
        return True

    def infer(self, image: Image.Image, params: Dict[str, Any]) -> ModelInferenceResult:
        logger.info("[MOCK] Starting inference for image size %s...", image.size)

        # 1. Simulate heavy computation
        time.sleep(self.processing_delay)

        # 2. Generate a simple 3D cube
        mesh = trimesh.creation.box(extents=[1, 1, 1])
        mesh.visual.vertex_colors = [100, 149, 237, 255]  # Cornflower blue

        # Export as GLB (binary glTF) — supported by model-viewer
        with io.BytesIO() as f:
            mesh.export(f, file_type="glb")
            mesh_bytes = f.getvalue()

        # 3. Generate a placeholder texture
        texture_img = Image.new("RGB", (512, 512), color="gray")
        with io.BytesIO() as f:
            texture_img.save(f, format="PNG")
            texture_bytes = f.getvalue()

        # 4. Fake metrics
        metrics = {
            "chamfer_distance": 0.042,
            "iou_3d": 0.89,
            "inference_time_sec": self.processing_delay,
            "device_used": "mock_cpu",
            "mock_mode": True,
        }

        logger.info("[MOCK] Inference completed successfully.")

        return ModelInferenceResult(
            success=True,
            mesh_bytes=mesh_bytes,
            texture_bytes=texture_bytes,
            metrics=metrics,
        )
