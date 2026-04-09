import io
import time
from typing import Dict, Any, Optional

import numpy as np
from PIL import Image

from .inference_interface import ModelInferenceInterface, ModelInferenceResult
from ..config.logging import get_logger

logger = get_logger(__name__)

FOREGROUND_RATIO = 0.85
CHUNK_SIZE = 8192
MODEL_NAME = "stabilityai/TripoSR"


class TripoSRService(ModelInferenceInterface):
    """
    TripoSR inference backend.

    Loads the pretrained TripoSR model and generates a 3D mesh from a
    single image. Supports both CPU and CUDA devices.

    Supports loading fine-tuned weights on top of the base model
    via the `finetuned_weights_path` parameter.

    Pipeline:
      1. Background removal (rembg)
      2. Inference -> scene_codes
      3. Mesh extraction (marching cubes)
      4. Export OBJ/GLB + texture
    """

    def __init__(
        self,
        device: str = "cpu",
        model_path: Optional[str] = None,
        finetuned_weights_path: Optional[str] = None,
        model_version: str = "base",
    ):
        self.device = device
        self.model_path = model_path
        self.finetuned_weights_path = finetuned_weights_path
        self.model_version = model_version
        self.model = None
        self._rembg_session = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the TripoSR model, optionally applying fine-tuned weights."""
        try:
            import torch
            from tsr.system import TSR

            logger.info("Loading TripoSR model on device=%s ...", self.device)
            start = time.monotonic()

            self.model = TSR.from_pretrained(
                MODEL_NAME,
                config_name="config.yaml",
                weight_name="model.ckpt",
            )
            self.model.renderer.set_chunk_size(CHUNK_SIZE)
            self.model.to(self.device)

            elapsed = time.monotonic() - start
            logger.info("TripoSR base model loaded in %.1fs on %s", elapsed, self.device)

            # Apply fine-tuned weights if specified
            if self.finetuned_weights_path:
                self._apply_finetuned_weights(torch)

        except ImportError as e:
            logger.error("TripoSR dependencies not installed: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to load TripoSR model: %s", e)
            raise

        try:
            import rembg
            self._rembg_session = rembg.new_session()
            logger.info("rembg session initialized for background removal")
        except ImportError:
            logger.warning("rembg not installed — background removal disabled")

    def _apply_finetuned_weights(self, torch) -> None:
        """Load fine-tuned weights on top of the base model."""
        from pathlib import Path

        weights_path = Path(self.finetuned_weights_path)

        # Support both direct .pt file and directory containing model_weights.pt
        if weights_path.is_dir():
            weights_file = weights_path / "model_weights.pt"
        else:
            weights_file = weights_path

        if not weights_file.exists():
            logger.warning(
                "Fine-tuned weights not found at %s, using base model",
                weights_file,
            )
            return

        try:
            start = time.monotonic()
            state_dict = torch.load(weights_file, map_location=self.device)
            self.model.load_state_dict(state_dict, strict=False)
            elapsed = time.monotonic() - start
            logger.info(
                "Fine-tuned weights loaded from %s in %.1fs (version=%s)",
                weights_file,
                elapsed,
                self.model_version,
            )
        except Exception as e:
            logger.error(
                "Failed to load fine-tuned weights from %s: %s. Using base model.",
                weights_file,
                e,
            )

    def reload_weights(self, finetuned_weights_path: Optional[str] = None, model_version: str = "base") -> bool:
        """Reload the model with different weights at runtime.

        Args:
            finetuned_weights_path: Path to fine-tuned weights, or None for base model
            model_version: Version identifier for metrics tracking

        Returns:
            True if reload succeeded
        """
        try:
            import torch

            self.finetuned_weights_path = finetuned_weights_path
            self.model_version = model_version
            self._load_model()
            return True
        except Exception as e:
            logger.error("Failed to reload model weights: %s", e)
            return False

    def is_available(self) -> bool:
        return self.model is not None

    def infer(self, image: Image.Image, params: Dict[str, Any]) -> ModelInferenceResult:
        """
        Generate a 3D mesh from an image via TripoSR.

        Supported params:
          - mc_resolution (int): marching cubes resolution, default 256
          - output_format (str): output file format, default 'obj'
          - remove_background (bool): remove background before inference, default True
          - foreground_ratio (float): foreground crop ratio, default 0.85
        """
        if not self.is_available():
            return ModelInferenceResult(success=False, error="Model not loaded")

        mc_resolution = params.get("mc_resolution", 256)
        output_format = params.get("output_format", "obj")
        remove_bg = params.get("remove_background", True)
        foreground_ratio = params.get("foreground_ratio", FOREGROUND_RATIO)

        logger.info(
            "Running TripoSR inference: image=%s, resolution=%d, format=%s, device=%s",
            image.size, mc_resolution, output_format, self.device,
        )

        start = time.monotonic()

        try:
            import torch

            # 1. Preprocess: background removal
            processed_image = self._preprocess_image(image, remove_bg, foreground_ratio)

            # 2. Inference
            with torch.no_grad():
                scene_codes = self.model([processed_image], device=self.device)
                meshes = self.model.extract_mesh(
                    scene_codes,
                    has_vertex_color=True,
                    resolution=mc_resolution,
                )

            if not meshes:
                return ModelInferenceResult(success=False, error="No mesh extracted")

            mesh = meshes[0]
            inference_time = time.monotonic() - start

            # 3. Export mesh to bytes
            mesh_bytes = self._export_mesh(mesh, output_format)

            # 4. Export texture if available
            texture_bytes = self._export_texture(mesh)

            vertices_count = len(mesh.vertices) if hasattr(mesh, "vertices") else 0
            faces_count = len(mesh.faces) if hasattr(mesh, "faces") else 0

            metrics = {
                "inference_time_sec": round(inference_time, 3),
                "device_used": self.device,
                "mc_resolution": mc_resolution,
                "vertices": vertices_count,
                "faces": faces_count,
                "background_removed": remove_bg and self._rembg_session is not None,
                "mock_mode": False,
                "model_version": self.model_version,
                "is_finetuned": self.finetuned_weights_path is not None,
            }

            logger.info(
                "TripoSR inference completed in %.2fs (%d verts, %d faces)",
                inference_time, vertices_count, faces_count,
            )

            return ModelInferenceResult(
                success=True,
                mesh_bytes=mesh_bytes,
                texture_bytes=texture_bytes,
                metrics=metrics,
            )

        except Exception as e:
            logger.error("TripoSR inference failed: %s", e, exc_info=True)
            return ModelInferenceResult(success=False, error=str(e))

    def _preprocess_image(
        self, image: Image.Image, remove_bg: bool, foreground_ratio: float
    ) -> Image.Image:
        """Remove background and resize foreground (matches streamlit_app.py pipeline)."""
        if not remove_bg or self._rembg_session is None:
            return image

        try:
            from tsr.utils import remove_background, resize_foreground

            processed = remove_background(image, self._rembg_session)
            processed = resize_foreground(processed, foreground_ratio)

            # RGBA -> RGB with gray background (0.5)
            img_array = np.array(processed).astype(np.float32) / 255.0
            if img_array.shape[2] == 4:
                alpha = img_array[:, :, 3:4]
                img_array = img_array[:, :, :3] * alpha + (1 - alpha) * 0.5

            return Image.fromarray((img_array * 255.0).astype(np.uint8))

        except Exception as e:
            logger.warning("Background removal failed, using original image: %s", e)
            return image

    @staticmethod
    def _export_mesh(mesh, fmt: str) -> bytes:
        """Export mesh to bytes."""
        import trimesh

        if not isinstance(mesh, trimesh.Trimesh):
            mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces)

        buf = io.BytesIO()
        mesh.export(buf, file_type=fmt)
        return buf.getvalue()

    @staticmethod
    def _export_texture(mesh) -> Optional[bytes]:
        """Export texture from mesh if available."""
        try:
            if hasattr(mesh, "visual") and hasattr(mesh.visual, "material"):
                material = mesh.visual.material
                if hasattr(material, "image") and material.image is not None:
                    buf = io.BytesIO()
                    material.image.save(buf, format="PNG")
                    return buf.getvalue()
        except Exception as e:
            logger.warning("Could not export texture: %s", e)
        return None
