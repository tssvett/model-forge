"""Fine-tuning configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


@dataclass
class FinetuningConfig:
    """Configuration for TripoSR fine-tuning pipeline."""

    # Dataset paths
    dataset_root: Path = field(default_factory=lambda: Path("data/shapenet"))
    dataset_type: str = "shapenet"  # "shapenet" or "objaverse"

    # Split ratios (must sum to 1.0)
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1

    # Data loading
    batch_size: int = 4
    num_workers: int = 2
    image_size: int = 512

    # Augmentation
    augmentation_enabled: bool = True
    augmentation_horizontal_flip: bool = True
    augmentation_rotation_degrees: float = 15.0
    augmentation_color_jitter: bool = True
    augmentation_brightness: float = 0.2
    augmentation_contrast: float = 0.2

    # Filtering
    categories: Optional[List[str]] = None  # None = all categories
    min_vertices: int = 100  # Skip degenerate meshes
    max_vertices: int = 500_000

    # Reproducibility
    seed: int = 42

    def __post_init__(self):
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Split ratios must sum to 1.0, got {total:.4f} "
                f"(train={self.train_ratio}, val={self.val_ratio}, test={self.test_ratio})"
            )
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}")
        self.dataset_root = Path(self.dataset_root)
