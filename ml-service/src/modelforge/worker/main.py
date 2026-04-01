#!/usr/bin/env python3
"""ModelForge ML Worker entry point."""

import sys

from ..config.settings import settings
from ..config.logging import setup_logging, get_logger
from ..metrics import start_metrics_server, WORKER_INFO
from .app import create_app

METRICS_PORT = 8000


def main() -> None:
    """Main entry point."""
    setup_logging(settings)
    logger = get_logger(__name__)

    try:
        # Start Prometheus metrics endpoint
        start_metrics_server(METRICS_PORT)
        WORKER_INFO.info({
            "version": settings.app_version,
            "environment": settings.environment,
            "mock_mode": str(settings.ml_mock_mode),
            "device": settings.tripsr_device,
        })

        logger.info(
            "Starting ModelForge ML Worker...",
            extra={
                "version": settings.app_version,
                "environment": settings.environment,
                "mock_mode": settings.ml_mock_mode,
            },
        )

        app = create_app(settings)
        app.run()

        logger.info("ML Worker shutdown complete")

    except KeyboardInterrupt:
        logger.warning("Received shutdown signal")
        sys.exit(0)
    except Exception as e:
        logger.error("Application failed to start: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
