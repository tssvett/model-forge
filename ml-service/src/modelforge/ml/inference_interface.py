from abc import ABC, abstractmethod
from PIL import Image
from typing import Dict, Any, Optional


class ModelInferenceResult:
    """
    Унифицированный результат работы ML-модели.
    """

    def __init__(
            self,
            success: bool,
            mesh_bytes: Optional[bytes] = None,
            texture_bytes: Optional[bytes] = None,
            metrics: Optional[Dict[str, Any]] = None,
            error: Optional[str] = None
    ):
        self.success = success
        self.mesh_bytes = mesh_bytes
        self.texture_bytes = texture_bytes
        self.metrics = metrics or {}
        self.error = error


class ModelInferenceInterface(ABC):
    """
    Абстрактный интерфейс для ML-модели.

    Позволяет менять реализацию (Mock -> TripoSR -> другая модель)
    без изменения кода в TaskProcessor.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Проверяет, готова ли модель к работе (загружена, есть GPU и т.д.)."""
        pass

    @abstractmethod
    def infer(self, image: Image.Image, params: Dict[str, Any]) -> ModelInferenceResult:
        """
        Запускает инференс.

        :param image: PIL Image (уже предобработанное)
        :param params: Словарь параметров (разрешение, формат и т.д.)
        :return: Объект с результатами
        """
        pass
