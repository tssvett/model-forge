import sys
import types
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

# Ensure rembg module exists for patching even if not installed
if "rembg" not in sys.modules:
    rembg_mock = types.ModuleType("rembg")
    rembg_mock.remove = MagicMock()
    sys.modules["rembg"] = rembg_mock

from modelforge.preprocessing.pipeline import ImagePreprocessor
from modelforge.config import Settings


@pytest.fixture
def settings():
    return Settings(ml_mock_mode=True, preprocess_image_size=512)


@pytest.fixture
def preprocessor(settings):
    return ImagePreprocessor(settings)


class TestImageValidation:

    def test_validate_rejects_tiny_image(self, preprocessor):
        """Слишком маленькое изображение (<64px) — ValueError."""
        tiny = Image.new("RGB", (32, 32))
        with pytest.raises(ValueError, match="too small"):
            preprocessor.preprocess(tiny, {"remove_background": False})

    def test_validate_rejects_huge_image(self, preprocessor):
        """Слишком большое изображение (>8192px) — ValueError."""
        huge = Image.new("RGB", (9000, 9000))
        with pytest.raises(ValueError, match="too large"):
            preprocessor.preprocess(huge, {"remove_background": False})

    def test_validate_accepts_normal_image(self, preprocessor):
        """Нормальное изображение проходит валидацию."""
        normal = Image.new("RGB", (256, 256))
        result = preprocessor.preprocess(normal, {"remove_background": False})
        assert result.size == (512, 512)


class TestBackgroundRemoval:

    def test_preprocess_removes_background(self, preprocessor):
        """При remove_background=True вызывается rembg."""
        input_img = Image.new("RGB", (256, 256))
        fake_result = Image.new("RGBA", (256, 256), (255, 0, 0, 255))

        with patch.dict(sys.modules, {"rembg": MagicMock(remove=MagicMock(return_value=fake_result))}):
            from importlib import reload
            import modelforge.preprocessing.pipeline as pipeline_mod

            result = preprocessor.preprocess(input_img, {"remove_background": True})

            sys.modules["rembg"].remove.assert_called_once()
            assert result.mode == "RGB"
            assert result.size == (512, 512)

    def test_preprocess_skips_background_removal(self, preprocessor):
        """При remove_background=False rembg не вызывается."""
        input_img = Image.new("RGB", (256, 256))
        mock_rembg = MagicMock()

        with patch.dict(sys.modules, {"rembg": mock_rembg}):
            preprocessor.preprocess(input_img, {"remove_background": False})
            mock_rembg.remove.assert_not_called()


class TestResizeAndPad:

    def test_resizes_large_image(self, preprocessor):
        """Большое изображение уменьшается до target_size."""
        large = Image.new("RGB", (2000, 1000))
        result = preprocessor.preprocess(large, {"remove_background": False})
        assert result.size == (512, 512)

    def test_pads_small_image(self, preprocessor):
        """Маленькое изображение центрируется с белым padding."""
        small = Image.new("RGB", (100, 100))
        result = preprocessor.preprocess(small, {"remove_background": False})
        assert result.size == (512, 512)

    def test_preserves_aspect_ratio(self, preprocessor):
        """Прямоугольное изображение сохраняет пропорции внутри квадрата."""
        rect = Image.new("RGB", (1000, 500), color=(255, 0, 0))
        result = preprocessor.preprocess(rect, {"remove_background": False})
        assert result.size == (512, 512)
        # Top-left corner should be white (padding area)
        top_left = result.getpixel((0, 0))
        assert top_left == (255, 255, 255)

    def test_square_image_no_padding(self, preprocessor):
        """Квадратное изображение точно target_size — без padding."""
        square = Image.new("RGB", (512, 512), color=(128, 128, 128))
        result = preprocessor.preprocess(square, {"remove_background": False})
        assert result.size == (512, 512)
        # Should not have white padding
        center = result.getpixel((256, 256))
        assert center == (128, 128, 128)

    def test_custom_target_size(self):
        """Кастомный target_size работает корректно."""
        s = Settings(ml_mock_mode=True, preprocess_image_size=256)
        p = ImagePreprocessor(s)
        img = Image.new("RGB", (100, 100))
        result = p.preprocess(img, {"remove_background": False})
        assert result.size == (256, 256)
