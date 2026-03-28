from .inference_interface import ModelInferenceInterface
from .mock_service import MockInferenceService
from ..config import Settings
from ..config.logging import get_logger

logger = get_logger(__name__)


def select_device(preferred: str) -> str:
    """
    Smart device selection.
    Attempts to import torch. Falls back to cpu if unavailable.
    """
    if preferred.startswith("cuda"):
        try:
            import torch

            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else "unknown"
                logger.info("GPU detected: %s", name)
                return preferred
            else:
                logger.warning("CUDA requested but not available. Falling back to CPU.")
                return "cpu"
        except ImportError:
            logger.warning("torch not installed. Falling back to CPU.")
            return "cpu"
    return "cpu"


def create_inference_service(settings: Settings) -> ModelInferenceInterface:
    """Factory method for creating the ML inference service."""

    # Mock mode (for load testing or when the model is not ready)
    if settings.ml_mock_mode:
        logger.info("Using MockInferenceService (mock mode)")
        return MockInferenceService(processing_delay=settings.ml_mock_delay)

    # Real mode — TripoSR
    try:
        logger.info("Initializing TripoSR inference service...")
        device = select_device(settings.tripsr_device)

        from .triposr_service import TripoSRService

        return TripoSRService(device=device, model_path=settings.tripsr_model_path)

    except ImportError as e:
        logger.error("TripoSR dependencies not installed: %s", e)
        logger.warning("Falling back to MockInferenceService. Install TripoSR deps or set ML_MOCK_MODE=true.")
        return MockInferenceService()
    except Exception as e:
        logger.error("Failed to initialize TripoSR: %s", e)
        logger.warning("Falling back to MockInferenceService for stability.")
        return MockInferenceService()
