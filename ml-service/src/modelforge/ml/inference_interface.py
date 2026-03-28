from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from PIL import Image


class ModelInferenceResult:
    """Unified result of an ML model inference run."""

    def __init__(
        self,
        success: bool,
        mesh_bytes: Optional[bytes] = None,
        texture_bytes: Optional[bytes] = None,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.mesh_bytes = mesh_bytes
        self.texture_bytes = texture_bytes
        self.metrics = metrics or {}
        self.error = error


class ModelInferenceInterface(ABC):
    """
    Abstract interface for an ML inference backend.

    Allows swapping implementations (Mock -> TripoSR -> other model)
    without changing TaskProcessor code.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the model is ready (loaded, GPU present, etc.)."""
        pass

    @abstractmethod
    def infer(self, image: Image.Image, params: Dict[str, Any]) -> ModelInferenceResult:
        """
        Run inference on an image.

        :param image: PIL Image (already preprocessed)
        :param params: Parameter dict (resolution, format, etc.)
        :return: Inference result object
        """
        pass
