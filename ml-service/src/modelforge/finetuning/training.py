"""Training loop for TripoSR fine-tuning.

Implements the core training loop with:
- Configurable optimizer and learning rate scheduling
- Checkpoint saving/loading
- Training metrics logging
- Validation loop with early stopping
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .config import FinetuningConfig, TrainingConfig
from .dataset import DatasetSplit, MeshData, ShapeNetDataset, create_data_loaders
from .losses import CombinedLoss, LossResult

logger = logging.getLogger(__name__)


@dataclass
class TrainingMetrics:
    """Metrics collected during a single training epoch."""

    epoch: int
    train_loss: float
    train_loss_components: Dict[str, float]
    val_loss: Optional[float] = None
    val_loss_components: Optional[Dict[str, float]] = None
    learning_rate: float = 0.0
    epoch_duration_sec: float = 0.0
    samples_processed: int = 0


@dataclass
class Checkpoint:
    """Training checkpoint data."""

    epoch: int
    best_val_loss: float
    train_losses: List[float]
    val_losses: List[float]
    training_config: Dict[str, Any]
    metrics_history: List[Dict[str, Any]]

    def save(self, path: Path) -> None:
        """Save checkpoint to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "epoch": self.epoch,
            "best_val_loss": self.best_val_loss,
            "train_losses": self.train_losses,
            "val_losses": self.val_losses,
            "training_config": self.training_config,
            "metrics_history": self.metrics_history,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Checkpoint saved: %s (epoch=%d, val_loss=%.6f)", path, self.epoch, self.best_val_loss)

    @classmethod
    def load(cls, path: Path) -> "Checkpoint":
        """Load checkpoint from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        logger.info("Checkpoint loaded: %s (epoch=%d)", path, data["epoch"])
        return cls(
            epoch=data["epoch"],
            best_val_loss=data["best_val_loss"],
            train_losses=data["train_losses"],
            val_losses=data["val_losses"],
            training_config=data["training_config"],
            metrics_history=data["metrics_history"],
        )


class LearningRateScheduler:
    """Learning rate scheduler with warmup and cosine annealing."""

    def __init__(self, config: TrainingConfig):
        self.base_lr = config.learning_rate
        self.warmup_epochs = config.warmup_epochs
        self.total_epochs = config.num_epochs
        self.min_lr = config.min_learning_rate
        self.schedule_type = config.lr_schedule

    def get_lr(self, epoch: int) -> float:
        """Get learning rate for given epoch."""
        if epoch < self.warmup_epochs:
            # Linear warmup
            return self.base_lr * (epoch + 1) / self.warmup_epochs

        if self.schedule_type == "cosine":
            # Cosine annealing after warmup
            progress = (epoch - self.warmup_epochs) / max(
                1, self.total_epochs - self.warmup_epochs
            )
            return self.min_lr + 0.5 * (self.base_lr - self.min_lr) * (
                1 + np.cos(np.pi * progress)
            )

        if self.schedule_type == "step":
            # Step decay: halve LR every 1/3 of remaining epochs
            steps = (epoch - self.warmup_epochs) // max(
                1, (self.total_epochs - self.warmup_epochs) // 3
            )
            return max(self.min_lr, self.base_lr * (0.5 ** steps))

        # Constant LR
        return self.base_lr


class TripoSRTrainer:
    """Training loop for TripoSR fine-tuning.

    Orchestrates the training process using dataset, loss functions,
    and learning rate scheduling. Simulates gradient-based optimization
    by tracking loss evolution across epochs.

    In production with PyTorch/TripoSR model loaded, the _train_step
    and _compute_sample_loss methods would use actual model forward/backward
    passes. This implementation provides the full training infrastructure
    (checkpointing, scheduling, metrics, validation) that wraps around
    the model-specific training logic.
    """

    def __init__(
        self,
        finetuning_config: FinetuningConfig,
        training_config: TrainingConfig,
    ):
        self.ft_config = finetuning_config
        self.tr_config = training_config
        self.loss_fn = CombinedLoss(
            chamfer_weight=training_config.chamfer_weight,
            edge_weight=training_config.edge_weight,
            laplacian_weight=training_config.laplacian_weight,
            n_surface_points=training_config.n_surface_points,
        )
        self.scheduler = LearningRateScheduler(training_config)
        self.metrics_history: List[TrainingMetrics] = []
        self.best_val_loss = float("inf")
        self.epochs_without_improvement = 0

    def train(self) -> List[TrainingMetrics]:
        """Run the full training loop.

        Returns:
            List of TrainingMetrics for each epoch.
        """
        logger.info(
            "Starting training: epochs=%d, lr=%.6f, patience=%d",
            self.tr_config.num_epochs,
            self.tr_config.learning_rate,
            self.tr_config.early_stopping_patience,
        )

        # Load datasets
        datasets = create_data_loaders(self.ft_config)
        train_dataset = datasets[DatasetSplit.TRAIN]
        val_dataset = datasets[DatasetSplit.VAL]

        if len(train_dataset) == 0:
            logger.error("Training dataset is empty, cannot train")
            return []

        logger.info(
            "Datasets loaded: train=%d, val=%d",
            len(train_dataset),
            len(val_dataset),
        )

        # Resume from checkpoint if available
        start_epoch = self._maybe_load_checkpoint()

        for epoch in range(start_epoch, self.tr_config.num_epochs):
            epoch_start = time.time()
            lr = self.scheduler.get_lr(epoch)

            # Training phase
            train_loss = self._train_epoch(train_dataset, epoch, lr)

            # Validation phase
            val_loss = None
            val_components = None
            if len(val_dataset) > 0:
                val_loss_result = self._validate_epoch(val_dataset, epoch)
                val_loss = val_loss_result.total
                val_components = val_loss_result.components

            epoch_duration = time.time() - epoch_start

            # Record metrics
            metrics = TrainingMetrics(
                epoch=epoch,
                train_loss=train_loss.total,
                train_loss_components=train_loss.components,
                val_loss=val_loss,
                val_loss_components=val_components,
                learning_rate=lr,
                epoch_duration_sec=epoch_duration,
                samples_processed=len(train_dataset),
            )
            self.metrics_history.append(metrics)

            logger.info(
                "Epoch %d/%d: train_loss=%.6f, val_loss=%s, lr=%.6f, time=%.1fs",
                epoch + 1,
                self.tr_config.num_epochs,
                train_loss.total,
                f"{val_loss:.6f}" if val_loss is not None else "N/A",
                lr,
                epoch_duration,
            )

            # Checkpoint and early stopping
            if val_loss is not None:
                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                    self.epochs_without_improvement = 0
                    self._save_checkpoint(epoch, is_best=True)
                else:
                    self.epochs_without_improvement += 1

                if (
                    self.tr_config.early_stopping_patience > 0
                    and self.epochs_without_improvement >= self.tr_config.early_stopping_patience
                ):
                    logger.info(
                        "Early stopping at epoch %d (no improvement for %d epochs)",
                        epoch + 1,
                        self.tr_config.early_stopping_patience,
                    )
                    break

            # Periodic checkpoint
            if (epoch + 1) % self.tr_config.checkpoint_every == 0:
                self._save_checkpoint(epoch, is_best=False)

        logger.info(
            "Training complete: %d epochs, best_val_loss=%.6f",
            len(self.metrics_history),
            self.best_val_loss,
        )
        return self.metrics_history

    def _train_epoch(
        self,
        dataset: ShapeNetDataset,
        epoch: int,
        learning_rate: float,
    ) -> LossResult:
        """Run one training epoch over the dataset.

        Iterates through samples in batches, computing loss for each.
        In a full PyTorch implementation, this would include model.forward(),
        loss.backward(), and optimizer.step().
        """
        all_losses: List[LossResult] = []
        batch_size = self.ft_config.batch_size
        indices = list(range(len(dataset)))

        # Shuffle training data each epoch
        rng = np.random.RandomState(self.ft_config.seed + epoch)
        rng.shuffle(indices)

        for batch_start in range(0, len(indices), batch_size):
            batch_indices = indices[batch_start : batch_start + batch_size]
            batch_loss = self._train_step(dataset, batch_indices, learning_rate)
            if batch_loss is not None:
                all_losses.append(batch_loss)

        return self._aggregate_losses(all_losses)

    def _train_step(
        self,
        dataset: ShapeNetDataset,
        batch_indices: List[int],
        learning_rate: float,
    ) -> Optional[LossResult]:
        """Process a single training batch.

        Loads samples, computes loss against ground truth meshes.
        With a real model, this would:
        1. Run model.forward(images) to get predicted meshes
        2. Compute loss vs ground truth
        3. Call loss.backward() and optimizer.step()

        Currently computes loss between ground truth mesh variations
        to validate the loss computation pipeline.
        """
        batch_losses: List[LossResult] = []

        for idx in batch_indices:
            try:
                image, mesh, sample = dataset[idx]
                if not mesh.is_valid:
                    continue

                loss = self._compute_sample_loss(mesh)
                batch_losses.append(loss)
            except Exception as e:
                logger.debug("Skipping sample %d: %s", idx, e)

        if not batch_losses:
            return None

        return self._aggregate_losses(batch_losses)

    def _compute_sample_loss(self, target_mesh: MeshData) -> LossResult:
        """Compute loss for a single sample.

        With a real TripoSR model, this would compare the model's predicted
        mesh against the ground truth. Currently evaluates mesh quality
        metrics on the ground truth as a pipeline validation.
        """
        return self.loss_fn.compute(
            pred_vertices=target_mesh.vertices,
            pred_faces=target_mesh.faces,
            target_vertices=target_mesh.vertices,
            target_faces=target_mesh.faces,
        )

    def _validate_epoch(
        self,
        dataset: ShapeNetDataset,
        epoch: int,
    ) -> LossResult:
        """Run validation over the entire validation set."""
        all_losses: List[LossResult] = []

        for idx in range(len(dataset)):
            try:
                image, mesh, sample = dataset[idx]
                if not mesh.is_valid:
                    continue

                loss = self._compute_sample_loss(mesh)
                all_losses.append(loss)
            except Exception as e:
                logger.debug("Skipping val sample %d: %s", idx, e)

        return self._aggregate_losses(all_losses)

    def _aggregate_losses(self, losses: List[LossResult]) -> LossResult:
        """Average multiple loss results."""
        if not losses:
            return LossResult(total=float("inf"), components={})

        total = np.mean([l.total for l in losses])
        all_keys = losses[0].components.keys()
        components = {
            k: float(np.mean([l.components.get(k, 0.0) for l in losses]))
            for k in all_keys
        }

        return LossResult(total=float(total), components=components)

    def _save_checkpoint(self, epoch: int, is_best: bool) -> None:
        """Save training checkpoint."""
        checkpoint_dir = self.tr_config.checkpoint_dir
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint = Checkpoint(
            epoch=epoch,
            best_val_loss=self.best_val_loss,
            train_losses=[m.train_loss for m in self.metrics_history],
            val_losses=[m.val_loss for m in self.metrics_history if m.val_loss is not None],
            training_config={
                "num_epochs": self.tr_config.num_epochs,
                "learning_rate": self.tr_config.learning_rate,
                "chamfer_weight": self.tr_config.chamfer_weight,
                "edge_weight": self.tr_config.edge_weight,
                "laplacian_weight": self.tr_config.laplacian_weight,
            },
            metrics_history=[
                {
                    "epoch": m.epoch,
                    "train_loss": m.train_loss,
                    "val_loss": m.val_loss,
                    "learning_rate": m.learning_rate,
                    "epoch_duration_sec": m.epoch_duration_sec,
                    "train_loss_components": m.train_loss_components,
                }
                for m in self.metrics_history
            ],
        )

        # Save periodic checkpoint
        path = checkpoint_dir / f"checkpoint_epoch_{epoch:04d}.json"
        checkpoint.save(path)

        # Save best model checkpoint
        if is_best:
            best_path = checkpoint_dir / "checkpoint_best.json"
            checkpoint.save(best_path)
            logger.info("New best model at epoch %d (val_loss=%.6f)", epoch + 1, self.best_val_loss)

    def _maybe_load_checkpoint(self) -> int:
        """Try to resume from the latest checkpoint. Returns start epoch."""
        if not self.tr_config.resume_from_checkpoint:
            return 0

        best_path = self.tr_config.checkpoint_dir / "checkpoint_best.json"
        if not best_path.exists():
            logger.info("No checkpoint found at %s, starting from scratch", best_path)
            return 0

        try:
            checkpoint = Checkpoint.load(best_path)
            self.best_val_loss = checkpoint.best_val_loss
            start_epoch = checkpoint.epoch + 1
            logger.info(
                "Resuming from epoch %d (best_val_loss=%.6f)",
                start_epoch,
                self.best_val_loss,
            )
            return start_epoch
        except Exception as e:
            logger.warning("Failed to load checkpoint: %s, starting from scratch", e)
            return 0

    def get_training_summary(self) -> Dict[str, Any]:
        """Return a summary of the training run."""
        if not self.metrics_history:
            return {"status": "no_training_data"}

        train_losses = [m.train_loss for m in self.metrics_history]
        val_losses = [m.val_loss for m in self.metrics_history if m.val_loss is not None]

        return {
            "total_epochs": len(self.metrics_history),
            "best_val_loss": self.best_val_loss,
            "final_train_loss": train_losses[-1],
            "final_val_loss": val_losses[-1] if val_losses else None,
            "train_loss_start": train_losses[0],
            "train_loss_end": train_losses[-1],
            "total_samples_processed": sum(m.samples_processed for m in self.metrics_history),
            "total_time_sec": sum(m.epoch_duration_sec for m in self.metrics_history),
            "early_stopped": self.epochs_without_improvement >= self.tr_config.early_stopping_patience
            if self.tr_config.early_stopping_patience > 0
            else False,
        }
