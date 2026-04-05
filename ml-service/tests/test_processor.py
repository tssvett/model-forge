import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, ANY
from PIL import Image
from pydantic import ValidationError

from modelforge.tasks.processor import TaskProcessor
from modelforge.tasks.models import TaskRequest, InputData, ProcessingParams
from modelforge.config import Settings
from modelforge.ml.inference_interface import ModelInferenceResult


@pytest.fixture
def mock_repository():
    repo = Mock()
    repo.get_app_settings.return_value = None
    return repo


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

    @patch('modelforge.tasks.processor.Image')
    def test_process_success(self, mock_image, processor, mock_repository, mock_storage):
        """Тест успешной обработки задачи."""
        mock_storage.download_file.return_value = b"fake image"
        mock_storage.upload_bytes.side_effect = lambda k, d: f"s3://bucket/{k}"
        fake_img = MagicMock(spec=Image.Image)
        fake_img.size = (256, 256)
        mock_image.open.return_value.convert.return_value = fake_img
        processor.preprocessor = Mock()
        processor.preprocessor.preprocess.return_value = fake_img

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
            ANY  # S3 key string
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
            mock_repository.update_status.assert_any_call("test-456", 'FAILED', error_msg=ANY)

    def test_process_validation_error(self, processor, mock_repository):
        """Тест ошибки валидации Pydantic (некорректное сообщение)."""
        task_data = {"task_id": "test-789"}  # missing required 'input' field
        result = processor.process(task_data)

        assert result is False
        mock_repository.update_status.assert_any_call("test-789", 'FAILED', error_msg=ANY)

    def test_process_invalid_output_format(self, processor, mock_repository):
        """Тест ошибки валидации — недопустимый output_format."""
        task_data = {
            "task_id": "test-bad-format",
            "input": {"s3_path": "s3://input/test.jpg"},
            "params": {"output_format": "invalid_format"}
        }
        result = processor.process(task_data)

        assert result is False
        mock_repository.update_status.assert_any_call("test-bad-format", 'FAILED', error_msg=ANY)


class TestTaskRequestModel:

    def test_valid_task_request(self):
        """Тест создания валидного TaskRequest."""
        task = TaskRequest(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            user_id="user-123",
            input=InputData(s3_path="s3://bucket/input.jpg"),
            params=ProcessingParams(output_format="obj", remove_background=True),
            created_at="2024-01-01T12:00:00Z",
        )
        assert task.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert task.input.s3_path == "s3://bucket/input.jpg"
        assert task.params.output_format == "obj"
        assert task.created_at == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    def test_default_params(self):
        """Тест значений по умолчанию для ProcessingParams."""
        task = TaskRequest(
            task_id="test-1",
            input={"s3_path": "s3://bucket/img.jpg"},
        )
        assert task.params.output_format == "glb"
        assert task.params.remove_background is True
        assert task.params.texture_quality == "high"

    def test_missing_task_id_raises(self):
        """Тест: отсутствие task_id вызывает ValidationError."""
        with pytest.raises(ValidationError):
            TaskRequest(input={"s3_path": "s3://bucket/img.jpg"})

    def test_missing_input_raises(self):
        """Тест: отсутствие input вызывает ValidationError."""
        with pytest.raises(ValidationError):
            TaskRequest(task_id="test-1")

    def test_empty_s3_path_raises(self):
        """Тест: пустой s3_path вызывает ValidationError."""
        with pytest.raises(ValidationError):
            TaskRequest(task_id="test-1", input={"s3_path": ""})

    def test_invalid_output_format_raises(self):
        """Тест: недопустимый output_format вызывает ValidationError."""
        with pytest.raises(ValidationError):
            TaskRequest(
                task_id="test-1",
                input={"s3_path": "s3://bucket/img.jpg"},
                params={"output_format": "invalid"},
            )
