import pytest
from unittest.mock import Mock, patch

from modelforge.worker.app import App, create_app
from modelforge.config import Settings


class TestApp:

    @pytest.fixture
    def settings(self):
        return Settings(worker_mock_delay=0)

    def test_create_app(self, settings):
        """Тест factory function."""
        app = create_app(settings)
        assert isinstance(app, App)
        assert app.settings == settings

    @patch('modelforge.worker.app.KafkaConsumerService')
    @patch('modelforge.worker.app.TaskRepository')
    @patch('modelforge.worker.app.S3StorageService')
    def test_app_initialization(self, mock_storage, mock_repo, mock_consumer, settings):
        """Тест инициализации приложения."""
        app = App(settings)

        assert app.consumer is not None
        assert app.repository is not None
        assert app.storage is not None
        assert app.processor is not None

    def test_app_shutdown(self, settings):
        """Тест корректного завершения работы."""
        app = App(settings)
        app._running = True
        app.shutdown()
        assert app._running == False
