#!/usr/bin/env python3
"""
Точка входа приложения ModelForge ML Worker.
"""

import sys
from ..config.settings import settings
from ..config.logging import setup_logging, get_logger
from .app import create_app


def main() -> None:
    """Main entry point."""
    # Настраиваем логирование ПЕРЕД созданием любых логгеров
    setup_logging(settings)

    logger = get_logger(__name__)

    try:
        logger.info("Starting ModelForge ML Worker...", extra={
            "version": settings.app_version,
            "environment": settings.environment,
            "mock_mode": settings.ml_mock_mode
        })

        app = create_app(settings)
        app.run()

        logger.info("ML Worker shutdown complete")

    except KeyboardInterrupt:
        logger.warning("Received shutdown signal")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
