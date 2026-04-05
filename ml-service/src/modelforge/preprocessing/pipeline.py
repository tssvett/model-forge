"""Image preprocessing pipeline: validation, background removal, resize/pad."""

import time
from typing import Dict, Any

from PIL import Image

from ..config import Settings
from ..config.logging import get_logger
from ..metrics.collector import PREPROCESSING_DURATION

logger = get_logger(__name__)

MIN_IMAGE_SIZE = 64
MAX_IMAGE_SIZE = 8192


class ImagePreprocessor:
    """Preprocesses images before ML inference: validate, remove background, resize."""

    def __init__(self, settings: Settings):
        self.target_size = settings.preprocess_image_size

    def preprocess(self, image: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """
        Full preprocessing pipeline.

        :param image: PIL Image in RGB mode
        :param params: Task params dict (uses 'remove_background' flag)
        :return: Preprocessed PIL Image (RGB, square, target_size x target_size)
        """
        start = time.monotonic()

        self._validate(image)

        if params.get("remove_background", True):
            image = self._remove_background(image)

        image = self._resize_and_pad(image)

        duration = time.monotonic() - start
        PREPROCESSING_DURATION.observe(duration)
        logger.info(
            "Preprocessing complete in %.2fs (final size: %s)",
            duration,
            image.size,
        )
        return image

    def _validate(self, image: Image.Image) -> None:
        """Validate image dimensions."""
        w, h = image.size
        if w < MIN_IMAGE_SIZE or h < MIN_IMAGE_SIZE:
            raise ValueError(
                f"Image too small: {w}x{h}, minimum is {MIN_IMAGE_SIZE}x{MIN_IMAGE_SIZE}"
            )
        if w > MAX_IMAGE_SIZE or h > MAX_IMAGE_SIZE:
            raise ValueError(
                f"Image too large: {w}x{h}, maximum is {MAX_IMAGE_SIZE}x{MAX_IMAGE_SIZE}"
            )

    def _remove_background(self, image: Image.Image) -> Image.Image:
        """Remove background using rembg, composite on white."""
        from rembg import remove

        logger.info("Removing background from image %s...", image.size)
        result = remove(image)  # returns RGBA

        # Composite on white background to get clean RGB
        background = Image.new("RGBA", result.size, (255, 255, 255, 255))
        background.paste(result, mask=result.split()[3])
        return background.convert("RGB")

    def _resize_and_pad(self, image: Image.Image) -> Image.Image:
        """Resize preserving aspect ratio, then center-pad to square."""
        w, h = image.size
        scale = self.target_size / max(w, h)

        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            image = image.resize((new_w, new_h), Image.LANCZOS)
        else:
            new_w, new_h = w, h

        # Center-pad to target_size x target_size
        if new_w == self.target_size and new_h == self.target_size:
            return image

        padded = Image.new("RGB", (self.target_size, self.target_size), (255, 255, 255))
        offset_x = (self.target_size - new_w) // 2
        offset_y = (self.target_size - new_h) // 2
        padded.paste(image, (offset_x, offset_y))
        return padded
