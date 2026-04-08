"""Fine-tuning configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional, List


@dataclass
class TrainingConfig:
    """Configuration for the training loop."""

    # Training hyperparameters
    num_epochs: int = 50
    learning_rate: float = 1e-4
    min_learning_rate: float = 1e-6
    warmup_epochs: int = 3
    lr_schedule: Literal["cosine", "step", "constant"] = "cosine"

    # Loss weights
    chamfer_weight: float = 1.0
    edge_weight: float = 0.1
    laplacian_weight: float = 0.05

    # Checkpointing
    checkpoint_dir: Path = field(default_factory=lambda: Path("checkpoints/triposr"))
    checkpoint_every: int = 5
    resume_from_checkpoint: bool = False

    # Loss computation
    n_surface_points: int = 4096

    # Early stopping
    early_stopping_patience: int = 10

    def __post_init__(self):
        if self.num_epochs < 1:
            raise ValueError(f"num_epochs must be >= 1, got {self.num_epochs}")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be > 0, got {self.learning_rate}")
        if self.warmup_epochs < 0:
            raise ValueError(f"warmup_epochs must be >= 0, got {self.warmup_epochs}")
        if self.warmup_epochs >= self.num_epochs:
            raise ValueError(
                f"warmup_epochs ({self.warmup_epochs}) must be < num_epochs ({self.num_epochs})"
            )
        self.checkpoint_dir = Path(self.checkpoint_dir)


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
