#!/usr/bin/env python3
"""
Точка входа приложения ModelForge ML Worker.
"""

import logging
import sys

from .app import create_app
from ..config import settings


def setup_logging() -> None:
    """Настраивает логирование приложения."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )


def main() -> None:
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting ModelForge ML Worker...")
        app = create_app(settings)
        app.run()
    except Exception as e:
        logger.error(f"Application failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
