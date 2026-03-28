"""
Structured logging configuration for ModelForge.
JSON format for Loki/Grafana compatibility.
"""

import logging
import sys
from typing import Optional, TYPE_CHECKING
from pythonjsonlogger import jsonlogger

# Lazy import to avoid circular dependencies
if TYPE_CHECKING:
    from ..config.settings import Settings


def setup_logging(settings_obj: "Settings") -> logging.Logger:
    """
    Configure application logging based on a Settings object.

    Args:
        settings_obj: Settings instance with logging configuration

    Returns:
        Configured root logger
    """
    numeric_level = getattr(logging, settings_obj.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear old handlers (in case of repeated calls in tests)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if settings_obj.log_format == "json":
        # JSON format for Loki: each log entry is a structured object
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    else:
        # Human-readable format for local development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Inject extra fields via filter
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
    Return a logger with the given name.
    Usage: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
