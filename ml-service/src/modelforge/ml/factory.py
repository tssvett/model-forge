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

        # Resolve fine-tuned weights path via weight manager
        finetuned_weights_path = None
        model_version = settings.model_version

        if model_version != "base":
            finetuned_weights_path = _resolve_finetuned_weights(
                settings, model_version
            )

        return TripoSRService(
            device=device,
            model_path=settings.tripsr_model_path,
            finetuned_weights_path=finetuned_weights_path,
            model_version=model_version,
        )

    except ImportError as e:
        logger.error("TripoSR dependencies not installed: %s", e)
        logger.warning("Falling back to MockInferenceService. Install TripoSR deps or set ML_MOCK_MODE=true.")
        return MockInferenceService()
    except Exception as e:
        logger.error("Failed to initialize TripoSR: %s", e)
        logger.warning("Falling back to MockInferenceService for stability.")
        return MockInferenceService()


def _resolve_finetuned_weights(settings: Settings, model_version: str) -> str | None:
    """Resolve the checkpoint path for a fine-tuned model version.

    Uses the WeightManager to look up the registered checkpoint path.
    Falls back to scanning the checkpoint directory if not registered.
    """
    from pathlib import Path
    from ..finetuning.weight_manager import WeightManager

    try:
        checkpoint_dir = Path(settings.training_checkpoint_dir)
        manager = WeightManager(
            checkpoint_dir=checkpoint_dir,
            s3_prefix=settings.checkpoint_s3_prefix,
        )

        path = manager.get_checkpoint_path(model_version)
        if path:
            logger.info(
                "Resolved fine-tuned weights for version '%s': %s",
                model_version, path,
            )
            return path

        logger.warning(
            "Model version '%s' not found in registry. Using base model.",
            model_version,
        )
        return None

    except Exception as e:
        logger.error("Failed to resolve fine-tuned weights: %s", e)
        return None
