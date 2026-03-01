"""
Модуль настройки структурированного логирования для ModelForge.
Логи в формате JSON для совместимости с Loki/Grafana.
"""

import logging
import sys
import os
from typing import Optional, TYPE_CHECKING
from pythonjsonlogger import jsonlogger

# Lazy import settings, чтобы избежать циклических зависимостей
if TYPE_CHECKING:
    from ..config.settings import Settings


def setup_logging(settings_obj: "Settings") -> logging.Logger:
    """
    Настраивает логирование приложения на основе объекта Settings.

    Args:
        settings_obj: Экземпляр Settings с конфигурацией

    Returns:
        Настроенный root-логгер
    """
    numeric_level = getattr(logging, settings_obj.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Очищаем старые хендлеры (на случай повторного вызова в тестах)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if settings_obj.log_format == "json":
        # JSON-формат для Loki: каждый лог — это объект с полями
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d",
            datefmt="%Y-%m-%dT%H:%M:%S%z"
        )
    else:
        # Человекочитаемый формат для локальной разработки
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Добавляем extra-поля через фильтр
    class ServiceFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.service = settings_obj.service_name
            record.environment = settings_obj.environment
            record.version = settings_obj.app_version
            return True

    handler.addFilter(ServiceFilter())

    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.
    Используется в модулях: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
