import pytest
from unittest.mock import Mock, MagicMock, patch
from PIL import Image

from modelforge.tasks.processor import TaskProcessor
from modelforge.config import Settings
from modelforge.ml.inference_interface import ModelInferenceResult


@pytest.fixture
def mock_repository():
    return Mock()


@pytest.fixture
def mock_storage():
    return Mock()


@pytest.fixture
def settings():
    return Settings(ml_mock_mode=True, ml_mock_delay=0)


@pytest.fixture
def processor(mock_repository, mock_storage, settings):
    with patch('modelforge.tasks.processor.create_inference_service') as mock_factory:
        mock_ml = Mock()
        mock_ml.infer.return_value = ModelInferenceResult(
            success=True,
            mesh_bytes=b"fake obj content",
            texture_bytes=b"fake png content",
            metrics={"mock": True}
        )
        mock_factory.return_value = mock_ml
        return TaskProcessor(
            repository=mock_repository,
            storage=mock_storage,
            settings=settings
        )


class TestTaskProcessor:

    def test_process_success(self, processor, mock_repository, mock_storage):
        """Тест успешной обработки задачи."""
        mock_storage.download_file.return_value = b"fake image"
        mock_storage.upload_bytes.side_effect = lambda k, d: f"s3://bucket/{k}"

        task_data = {
            "task_id": "test-123",
            "input": {"s3_path": "s3://input/test.jpg"},
            "params": {"output_format": "obj"}
        }

        result = processor.process(task_data)

        assert result is True
        mock_repository.update_status.assert_any_call("test-123", 'PROCESSING')
        mock_repository.update_status.assert_any_call(
            "test-123",
            'COMPLETED',
            pytest.any(str)  # JSON string with results
        )

    def test_process_failure_ml_error(self, processor, mock_repository):
        """Тест неудачной обработки (ошибка ML)."""
        with patch.object(processor.ml_service, 'infer') as mock_infer:
            mock_infer.return_value = ModelInferenceResult(
                success=False,
                error="Test ML error"
            )

            task_data = {"task_id": "test-456", "input": {"s3_path": "s3://input/test.jpg"}}
            result = processor.process(task_data)

            assert result is False
            mock_repository.update_status.assert_any_call("test-456", 'FAILED')
