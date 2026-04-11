"""Training loop for TripoSR fine-tuning.

Implements the core training loop with:
- Real TripoSR model forward/backward passes (when available)
- Differentiable occupancy-based loss on the density field
- Mesh-level Chamfer/edge/Laplacian metrics for monitoring
- Configurable optimizer and learning rate scheduling
- Checkpoint saving/loading (including model weights)
- Validation loop with early stopping
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

from .config import FinetuningConfig, TrainingConfig
from .dataset import DatasetSplit, MeshData, ShapeNetDataset, create_data_loaders
from .losses import CombinedLoss, LossResult, sample_surface_points

logger = logging.getLogger(__name__)

FOREGROUND_RATIO = 0.85
RENDERER_CHUNK_SIZE = 8192
DEFAULT_MODEL_NAME = "stabilityai/TripoSR"


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

    When the TripoSR model and PyTorch are available, performs real
    gradient-based training:
    1. Forward pass: image -> scene_codes (triplane features)
    2. Query density field at sampled 3D points (differentiable)
    3. Compute occupancy loss vs ground truth mesh surface
    4. Backward pass and optimizer step
    5. Extract predicted mesh for Chamfer/edge/Laplacian monitoring

    When TripoSR is not installed (e.g., in tests), falls back to stub
    mode that validates the loss computation pipeline using ground truth
    meshes directly.
    """

    def __init__(
        self,
        finetuning_config: FinetuningConfig,
        training_config: TrainingConfig,
        device: str = "cpu",
        model_name: str = DEFAULT_MODEL_NAME,
    ):
        self.ft_config = finetuning_config
        self.tr_config = training_config
        self.device = device
        self.model_name = model_name
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

        # Model components (initialized lazily via _ensure_model_loaded)
        self.model = None
        self.optimizer = None
        self._torch = None
        self._rembg_session = None

    def _ensure_model_loaded(self) -> bool:
        """Load the TripoSR model for training if available.

        Returns True if the model was loaded successfully, False otherwise.
        When False, the trainer falls back to stub mode.
        """
        if self.model is not None:
            return True

        try:
            import torch
            self._torch = torch
            from tsr.system import TSR

            logger.info(
                "Loading TripoSR model '%s' on device=%s...",
                self.model_name, self.device,
            )
            start = time.time()

            self.model = TSR.from_pretrained(
                self.model_name,
                config_name="config.yaml",
                weight_name="model.ckpt",
            )
            self.model.renderer.set_chunk_size(RENDERER_CHUNK_SIZE)
            self.model.to(self.device)
            self.model.train()

            # Optimizer for trainable parameters
            trainable = [p for p in self.model.parameters() if p.requires_grad]
            self.optimizer = torch.optim.AdamW(
                trainable,
                lr=self.tr_config.learning_rate,
                weight_decay=1e-4,
            )

            elapsed = time.time() - start
            n_total = sum(p.numel() for p in self.model.parameters())
            n_trainable = sum(p.numel() for p in trainable)
            logger.info(
                "TripoSR loaded in %.1fs: %d params (%d trainable)",
                elapsed, n_total, n_trainable,
            )

            # Background removal for image preprocessing
            try:
                import rembg
                self._rembg_session = rembg.new_session()
                logger.info("rembg session initialized")
            except ImportError:
                logger.warning("rembg not installed, background removal disabled")

            return True

        except ImportError as e:
            logger.warning(
                "TripoSR dependencies not available: %s. Using stub training mode.", e
            )
            return False

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for TripoSR input (background removal + foreground resize)."""
        if self._rembg_session is None:
            return image

        try:
            from tsr.utils import remove_background, resize_foreground

            processed = remove_background(image, self._rembg_session)
            processed = resize_foreground(processed, FOREGROUND_RATIO)

            # RGBA -> RGB with gray background
            arr = np.array(processed).astype(np.float32) / 255.0
            if arr.shape[-1] == 4:
                alpha = arr[:, :, 3:4]
                arr = arr[:, :, :3] * alpha + (1 - alpha) * 0.5
            return Image.fromarray((arr * 255.0).astype(np.uint8))

        except Exception as e:
            logger.debug("Image preprocessing failed, using original: %s", e)
            return image

    def _query_density(self, positions, scene_code):
        """Query the TripoSR density field at arbitrary 3D positions.

        Uses the model's renderer to evaluate the triplane representation,
        which is fully differentiable for gradient-based training.

        Args:
            positions: (N, 3) tensor of 3D query points.
            scene_code: single scene code (triplane features) from forward pass.

        Returns:
            (N,) tensor of density values.
        """
        torch = self._torch
        chunk_size = RENDERER_CHUNK_SIZE
        densities = []

        for i in range(0, len(positions), chunk_size):
            chunk = positions[i : i + chunk_size]
            # query_triplane: standard TripoSR renderer API
            result = self.model.renderer.query_triplane(
                self.model.decoder,
                chunk.unsqueeze(0),  # (1, chunk_size, 3)
                scene_code,
            )
            # Extract density from renderer output
            if isinstance(result, dict):
                density = result.get(
                    "density_act", result.get("density", result.get("sigma"))
                )
            elif isinstance(result, (tuple, list)):
                density = result[0]
            else:
                density = result

            densities.append(density.view(-1))

        return torch.cat(densities)

    def _compute_occupancy_loss(self, scene_codes, target_mesh: MeshData):
        """Compute differentiable occupancy loss on the density field.

        Samples 3D points on and around the ground truth mesh surface,
        queries the model's predicted density at those points, and
        computes a binary cross-entropy loss:
        - Surface points should have HIGH density (label=1)
        - Random empty-space points should have LOW density (label=0)

        This loss is fully differentiable through the triplane decoder,
        enabling gradient-based fine-tuning of the entire model.
        """
        torch = self._torch
        scene_code = scene_codes[0]  # Single sample (batch size 1)

        # Sample points on GT mesh surface (positive samples)
        surface_pts = sample_surface_points(
            target_mesh.vertices,
            target_mesh.faces,
            n_points=self.tr_config.n_surface_points,
        )

        if len(surface_pts) == 0:
            return torch.tensor(0.0, device=self.device, requires_grad=True)

        # Sample random points in expanded bounding box (negative samples)
        bbox_min = target_mesh.vertices.min(axis=0) - 0.2
        bbox_max = target_mesh.vertices.max(axis=0) + 0.2
        n_random = self.tr_config.n_surface_points
        random_pts = np.random.uniform(
            bbox_min, bbox_max, size=(n_random, 3)
        ).astype(np.float32)

        # Combine surface (label=1) and random (label=0) points
        all_points = np.concatenate([surface_pts, random_pts], axis=0)
        labels = np.concatenate([
            np.ones(len(surface_pts), dtype=np.float32),
            np.zeros(n_random, dtype=np.float32),
        ])

        points_t = torch.from_numpy(all_points).to(self.device)
        labels_t = torch.from_numpy(labels).to(self.device)

        # Query density field (differentiable)
        density = self._query_density(points_t, scene_code)

        # BCE with logits (density values may be in logit space)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            density, labels_t, reduction="mean"
        )

        return loss

    def train(self) -> List[TrainingMetrics]:
        """Run the full training loop.

        Returns:
            List of TrainingMetrics for each epoch.
        """
        # Try to load TripoSR model; falls back to stub mode if unavailable
        has_model = self._ensure_model_loaded()
        mode = "model" if has_model else "stub"
        logger.info(
            "Starting training (%s mode): epochs=%d, lr=%.6f, patience=%d",
            mode,
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
        """Run one training epoch over the dataset."""
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

        Dispatches to the real training step (with model forward/backward)
        or the stub implementation (for testing without TripoSR).
        """
        if self.model is not None:
            return self._train_step_with_model(dataset, batch_indices, learning_rate)
        return self._train_step_stub(dataset, batch_indices)

    def _train_step_with_model(
        self,
        dataset: ShapeNetDataset,
        batch_indices: List[int],
        learning_rate: float,
    ) -> Optional[LossResult]:
        """Training step with real TripoSR model forward/backward passes.

        For each sample in the batch:
        1. Preprocess image and run forward pass -> scene_codes
        2. Compute differentiable occupancy loss on the density field
        3. Extract predicted mesh for Chamfer/edge/Laplacian monitoring

        After processing all samples:
        4. Average and backpropagate the occupancy loss
        5. Clip gradients and update model weights
        """
        torch = self._torch

        # Update learning rate for this step
        for param_group in self.optimizer.param_groups:
            param_group["lr"] = learning_rate

        self.optimizer.zero_grad()

        accumulated_occ_loss = None
        mesh_losses: List[LossResult] = []
        valid_count = 0

        for idx in batch_indices:
            try:
                image, mesh, sample = dataset[idx]
                if not mesh.is_valid:
                    continue

                # Forward pass: image -> scene_codes (differentiable)
                processed = self._preprocess_image(image)
                scene_codes = self.model([processed], device=self.device)

                # Differentiable occupancy loss for gradient computation
                occ_loss = self._compute_occupancy_loss(scene_codes, mesh)
                if accumulated_occ_loss is None:
                    accumulated_occ_loss = occ_loss
                else:
                    accumulated_occ_loss = accumulated_occ_loss + occ_loss
                valid_count += 1

                # Mesh-level metrics for monitoring (non-differentiable)
                with torch.no_grad():
                    pred_meshes = self.model.extract_mesh(
                        scene_codes, resolution=128
                    )
                    if pred_meshes:
                        pred = pred_meshes[0]
                        mesh_loss = self.loss_fn.compute(
                            np.asarray(pred.vertices, dtype=np.float32),
                            np.asarray(pred.faces, dtype=np.int64),
                            mesh.vertices,
                            mesh.faces,
                        )
                        mesh_losses.append(mesh_loss)

            except Exception as e:
                logger.debug("Skipping sample %d: %s", idx, e)

        # Backward pass and weight update
        if accumulated_occ_loss is not None and valid_count > 0:
            avg_occ_loss = accumulated_occ_loss / valid_count
            avg_occ_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

        if not mesh_losses:
            return None
        return self._aggregate_losses(mesh_losses)

    def _train_step_stub(
        self,
        dataset: ShapeNetDataset,
        batch_indices: List[int],
    ) -> Optional[LossResult]:
        """Stub training step for testing without TripoSR model.

        Computes loss between ground truth mesh variations to validate
        the loss computation pipeline.
        """
        batch_losses: List[LossResult] = []

        for idx in batch_indices:
            try:
                image, mesh, sample = dataset[idx]
                if not mesh.is_valid:
                    continue

                loss = self.loss_fn.compute(
                    pred_vertices=mesh.vertices,
                    pred_faces=mesh.faces,
                    target_vertices=mesh.vertices,
                    target_faces=mesh.faces,
                )
                batch_losses.append(loss)
            except Exception as e:
                logger.debug("Skipping sample %d: %s", idx, e)

        if not batch_losses:
            return None
        return self._aggregate_losses(batch_losses)

    def _compute_sample_loss(
        self, image: Image.Image, target_mesh: MeshData
    ) -> LossResult:
        """Compute mesh-level loss for a single sample (used in validation).

        With the real model: runs inference and compares predicted mesh
        against ground truth. Without: compares GT to itself (stub).
        """
        if self.model is not None:
            torch = self._torch
            with torch.no_grad():
                processed = self._preprocess_image(image)
                scene_codes = self.model([processed], device=self.device)
                pred_meshes = self.model.extract_mesh(scene_codes, resolution=128)
                if pred_meshes:
                    pred = pred_meshes[0]
                    return self.loss_fn.compute(
                        pred_vertices=np.asarray(pred.vertices, dtype=np.float32),
                        pred_faces=np.asarray(pred.faces, dtype=np.int64),
                        target_vertices=target_mesh.vertices,
                        target_faces=target_mesh.faces,
                    )

        # Stub fallback: evaluate mesh quality on ground truth
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
        """Run validation over the entire validation set (no gradient computation)."""
        # Switch model to eval mode for validation
        if self.model is not None:
            self.model.eval()

        all_losses: List[LossResult] = []

        for idx in range(len(dataset)):
            try:
                image, mesh, sample = dataset[idx]
                if not mesh.is_valid:
                    continue

                loss = self._compute_sample_loss(image, mesh)
                all_losses.append(loss)
            except Exception as e:
                logger.debug("Skipping val sample %d: %s", idx, e)

        # Restore training mode
        if self.model is not None:
            self.model.train()

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
        """Save training checkpoint (metrics JSON + model weights if available)."""
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

        # Save model weights (PyTorch state_dict)
        if self.model is not None and self._torch is not None:
            if is_best:
                weights_path = checkpoint_dir / "model_weights.pt"
                self._torch.save(self.model.state_dict(), weights_path)
                logger.info("Model weights saved: %s", weights_path)

            optimizer_path = checkpoint_dir / f"optimizer_epoch_{epoch:04d}.pt"
            self._torch.save(self.optimizer.state_dict(), optimizer_path)

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

            # Load model weights if available
            if self.model is not None and self._torch is not None:
                weights_path = self.tr_config.checkpoint_dir / "model_weights.pt"
                if weights_path.exists():
                    state_dict = self._torch.load(
                        weights_path, map_location=self.device
                    )
                    self.model.load_state_dict(state_dict, strict=False)
                    logger.info("Model weights loaded from %s", weights_path)

                # Load optimizer state from closest epoch
                opt_path = (
                    self.tr_config.checkpoint_dir
                    / f"optimizer_epoch_{checkpoint.epoch:04d}.pt"
                )
                if opt_path.exists():
                    opt_state = self._torch.load(
                        opt_path, map_location=self.device
                    )
                    self.optimizer.load_state_dict(opt_state)
                    logger.info("Optimizer state loaded from %s", opt_path)

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
            "model_mode": "real" if self.model is not None else "stub",
        }
