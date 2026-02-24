# src/modelforge/ml/factory.py
import logging
from ..config import Settings
from .inference_interface import ModelInferenceInterface
from .mock_service import MockInferenceService

logger = logging.getLogger(__name__)


def select_device(preferred: str) -> str:
    """
    Умный выбор устройства.
    Пытается импортировать torch. Если нет - возвращает cpu.
    """
    if preferred.startswith("cuda"):
        try:
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else "unknown"
                logger.info(f"🚀 GPU detected: {device_name}")
                return preferred
            else:
                logger.warning("⚠️ CUDA requested but not available. Falling back to CPU.")
                return "cpu"
        except ImportError:
            logger.warning("⚠️ torch not installed. Falling back to CPU.")
            return "cpu"
    return "cpu"


def create_inference_service(settings: Settings) -> ModelInferenceInterface:
    """
    Factory method для создания ML-сервиса.
    """

    # Режим Mock (для тестов нагрузки или если модель не готова)
    if settings.ml_mock_mode:
        logger.info("🔧 Using MockInferenceService (Mock Mode)")
        return MockInferenceService(processing_delay=settings.ml_mock_delay)

    # Режим Real (здесь потом включим TripoSR)
    try:
        logger.info("🔧 Attempting to initialize Real ML Service...")

        # TODO: Раскомментировать, когда модель TripoSR будет интегрирована
        # device = select_device(settings.tripsr_device)
        # from .tripors_service import TripoRSService
        # return TripoRSService(device=device, config=settings)

        # ВРЕМЕННО: Если реальный код еще не написан, падаем в Mock с предупреждением
        logger.warning("⚠️ Real ML service not implemented yet. Falling back to Mock.")
        return MockInferenceService()

    except ImportError as e:
        logger.error(f"❌ Failed to load Real ML Service: {e}")
        logger.warning("⚠️ Falling back to MockInferenceService for stability.")
        return MockInferenceService()
    except Exception as e:
        logger.error(f"❌ Unexpected error initializing ML service: {e}")
        logger.warning("⚠️ Falling back to MockInferenceService for stability.")
        return MockInferenceService()
