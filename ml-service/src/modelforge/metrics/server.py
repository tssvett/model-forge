"""Lightweight HTTP server exposing /metrics for Prometheus scraping."""

import threading

from prometheus_client import start_http_server

from ..config.logging import get_logger

logger = get_logger(__name__)

_server_started = False


def start_metrics_server(port: int = 8000) -> None:
    """Start the Prometheus metrics HTTP server in a daemon thread."""
    global _server_started
    if _server_started:
        return

    def _run():
        start_http_server(port)
        logger.info("Prometheus metrics server started on port %d", port)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    _server_started = True
