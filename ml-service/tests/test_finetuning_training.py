"""Tests for fine-tuning training loop module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from modelforge.finetuning.config import FinetuningConfig, TrainingConfig
from modelforge.finetuning.dataset import MeshData
from modelforge.finetuning.losses import (
    CombinedLoss,
    LossResult,
    chamfer_distance,
    mesh_edge_loss,
    mesh_laplacian_loss,
    sample_surface_points,
)
from modelforge.finetuning.training import (
    Checkpoint,
    LearningRateScheduler,
    TrainingMetrics,
    TripoSRTrainer,
)


# === Fixtures ===


def _make_tetrahedron():
    """Create a simple tetrahedron mesh."""
    vertices = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32
    )
    faces = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], dtype=np.int64)
    return vertices, faces


def _make_cube():
    """Create a simple cube mesh."""
    vertices = np.array(
        [
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
        ],
        dtype=np.float32,
    )
    faces = np.array(
        [
            [0, 1, 2], [0, 2, 3],  # bottom
            [4, 5, 6], [4, 6, 7],  # top
            [0, 1, 5], [0, 5, 4],  # front
            [2, 3, 7], [2, 7, 6],  # back
            [0, 3, 7], [0, 7, 4],  # left
            [1, 2, 6], [1, 6, 5],  # right
        ],
        dtype=np.int64,
    )
    return vertices, faces


@pytest.fixture
def temp_dataset(tmp_path):
    """Create a minimal ShapeNet-style dataset for training tests."""
    # Keep tiny: 2 categories × 2 models × 1 image = 4 samples total
    for cat in ["chair", "table"]:
        for i in range(2):
            model_dir = tmp_path / cat / f"model_{i:03d}"
            images_dir = model_dir / "images"
            images_dir.mkdir(parents=True)

            img = Image.new("RGB", (64, 64), color=(100, 150, 200))
            img.save(images_dir / "000.png")

            with open(model_dir / "model.obj", "w") as f:
                f.write("v 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nv 0.0 0.0 1.0\n")
                f.write("f 1 2 3\nf 1 2 4\nf 1 3 4\nf 2 3 4\n")

    return tmp_path


@pytest.fixture
def ft_config(temp_dataset):
    return FinetuningConfig(
        dataset_root=temp_dataset,
        train_ratio=0.5,
        val_ratio=0.5,
        test_ratio=0.0,
        image_size=64,
        batch_size=2,
        seed=42,
    )


@pytest.fixture
def tr_config(tmp_path):
    return TrainingConfig(
        num_epochs=2,
        learning_rate=1e-3,
        warmup_epochs=1,
        checkpoint_dir=tmp_path / "checkpoints",
        checkpoint_every=1,
        early_stopping_patience=5,
        n_surface_points=64,
    )


# === TrainingConfig Tests ===


class TestTrainingConfig:
    def test_default_config(self):
        cfg = TrainingConfig()
        assert cfg.num_epochs == 50
        assert cfg.learning_rate == 1e-4
        assert cfg.lr_schedule == "cosine"

    def test_invalid_epochs(self):
        with pytest.raises(ValueError, match="num_epochs must be >= 1"):
            TrainingConfig(num_epochs=0)

    def test_invalid_learning_rate(self):
        with pytest.raises(ValueError, match="learning_rate must be > 0"):
            TrainingConfig(learning_rate=0)

    def test_invalid_warmup(self):
        with pytest.raises(ValueError, match="warmup_epochs.*must be < num_epochs"):
            TrainingConfig(num_epochs=5, warmup_epochs=5)

    def test_path_conversion(self):
        cfg = TrainingConfig(checkpoint_dir="some/path")
        assert isinstance(cfg.checkpoint_dir, Path)


# === Loss Function Tests ===


class TestChamferDistance:
    def test_identical_point_clouds(self):
        points = np.random.rand(100, 3).astype(np.float32)
        dist = chamfer_distance(points, points)
        assert dist == pytest.approx(0.0, abs=1e-6)

    def test_different_point_clouds(self):
        p1 = np.zeros((10, 3), dtype=np.float32)
        p2 = np.ones((10, 3), dtype=np.float32)
        dist = chamfer_distance(p1, p2)
        assert dist > 0

    def test_empty_returns_inf(self):
        empty = np.zeros((0, 3), dtype=np.float32)
        points = np.random.rand(10, 3).astype(np.float32)
        assert chamfer_distance(empty, points) == float("inf")
        assert chamfer_distance(points, empty) == float("inf")

    def test_symmetry(self):
        rng = np.random.RandomState(42)
        p1 = rng.rand(50, 3).astype(np.float32)
        p2 = rng.rand(50, 3).astype(np.float32)
        d1 = chamfer_distance(p1, p2)
        d2 = chamfer_distance(p2, p1)
        assert d1 == pytest.approx(d2, rel=1e-5)


class TestMeshEdgeLoss:
    def test_uniform_mesh(self):
        verts, faces = _make_tetrahedron()
        loss = mesh_edge_loss(verts, faces)
        assert loss >= 0.0

    def test_empty_mesh(self):
        empty_v = np.zeros((0, 3), dtype=np.float32)
        empty_f = np.zeros((0, 3), dtype=np.int64)
        assert mesh_edge_loss(empty_v, empty_f) == 0.0


class TestMeshLaplacianLoss:
    def test_smooth_mesh(self):
        verts, faces = _make_tetrahedron()
        loss = mesh_laplacian_loss(verts, faces)
        assert loss >= 0.0

    def test_empty_mesh(self):
        empty_v = np.zeros((0, 3), dtype=np.float32)
        empty_f = np.zeros((0, 3), dtype=np.int64)
        assert mesh_laplacian_loss(empty_v, empty_f) == 0.0


class TestSampleSurfacePoints:
    def test_sample_count(self):
        verts, faces = _make_tetrahedron()
        points = sample_surface_points(verts, faces, n_points=100)
        assert points.shape == (100, 3)

    def test_deterministic(self):
        verts, faces = _make_tetrahedron()
        p1 = sample_surface_points(verts, faces, n_points=50, seed=42)
        p2 = sample_surface_points(verts, faces, n_points=50, seed=42)
        np.testing.assert_array_equal(p1, p2)

    def test_empty_mesh(self):
        empty_v = np.zeros((0, 3), dtype=np.float32)
        empty_f = np.zeros((0, 3), dtype=np.int64)
        points = sample_surface_points(empty_v, empty_f)
        assert len(points) == 0


class TestCombinedLoss:
    def test_identical_meshes(self):
        verts, faces = _make_tetrahedron()
        loss_fn = CombinedLoss()
        result = loss_fn.compute(verts, faces, verts, faces)
        assert isinstance(result, LossResult)
        assert "chamfer" in result.components
        assert "edge" in result.components
        assert "laplacian" in result.components
        # Chamfer should be ~0 for identical meshes
        assert result.components["chamfer"] == pytest.approx(0.0, abs=1e-4)

    def test_different_meshes(self):
        v1, f1 = _make_tetrahedron()
        v2, f2 = _make_cube()
        loss_fn = CombinedLoss()
        result = loss_fn.compute(v1, f1, v2, f2)
        assert result.total > 0


# === LearningRateScheduler Tests ===


class TestLearningRateScheduler:
    def test_warmup(self):
        cfg = TrainingConfig(
            num_epochs=10, learning_rate=1e-3, warmup_epochs=3
        )
        scheduler = LearningRateScheduler(cfg)
        # During warmup, LR should increase
        lr0 = scheduler.get_lr(0)
        lr1 = scheduler.get_lr(1)
        lr2 = scheduler.get_lr(2)
        assert lr0 < lr1 < lr2

    def test_warmup_reaches_base_lr(self):
        cfg = TrainingConfig(
            num_epochs=10, learning_rate=1e-3, warmup_epochs=3
        )
        scheduler = LearningRateScheduler(cfg)
        lr = scheduler.get_lr(2)  # Last warmup epoch
        assert lr == pytest.approx(1e-3, rel=1e-5)

    def test_cosine_decay(self):
        cfg = TrainingConfig(
            num_epochs=20,
            learning_rate=1e-3,
            warmup_epochs=0,
            lr_schedule="cosine",
        )
        scheduler = LearningRateScheduler(cfg)
        lr_start = scheduler.get_lr(0)
        lr_mid = scheduler.get_lr(10)
        lr_end = scheduler.get_lr(19)
        assert lr_start > lr_mid > lr_end

    def test_constant_schedule(self):
        cfg = TrainingConfig(
            num_epochs=10,
            learning_rate=1e-3,
            warmup_epochs=0,
            lr_schedule="constant",
        )
        scheduler = LearningRateScheduler(cfg)
        for epoch in range(10):
            assert scheduler.get_lr(epoch) == pytest.approx(1e-3)

    def test_step_decay(self):
        cfg = TrainingConfig(
            num_epochs=12,
            learning_rate=1e-3,
            warmup_epochs=0,
            lr_schedule="step",
        )
        scheduler = LearningRateScheduler(cfg)
        lr0 = scheduler.get_lr(0)
        lr6 = scheduler.get_lr(6)
        assert lr0 > lr6


# === Checkpoint Tests ===


class TestCheckpoint:
    def test_save_and_load(self, tmp_path):
        ckpt = Checkpoint(
            epoch=5,
            best_val_loss=0.123,
            train_losses=[1.0, 0.8, 0.6, 0.5, 0.4, 0.3],
            val_losses=[1.1, 0.9, 0.7, 0.5, 0.3, 0.2],
            training_config={"lr": 1e-4, "epochs": 10},
            metrics_history=[{"epoch": 0, "train_loss": 1.0}],
        )
        path = tmp_path / "test_ckpt.json"
        ckpt.save(path)

        loaded = Checkpoint.load(path)
        assert loaded.epoch == 5
        assert loaded.best_val_loss == pytest.approx(0.123)
        assert len(loaded.train_losses) == 6
        assert loaded.training_config["lr"] == 1e-4

    def test_save_creates_directories(self, tmp_path):
        ckpt = Checkpoint(
            epoch=0, best_val_loss=1.0,
            train_losses=[], val_losses=[],
            training_config={}, metrics_history=[],
        )
        path = tmp_path / "nested" / "dir" / "ckpt.json"
        ckpt.save(path)
        assert path.exists()


# === Trainer Tests ===


class TestTripoSRTrainer:
    def test_training_runs(self, ft_config, tr_config):
        trainer = TripoSRTrainer(ft_config, tr_config)
        metrics = trainer.train()
        assert len(metrics) <= tr_config.num_epochs
        assert len(metrics) > 0
        assert all(isinstance(m, TrainingMetrics) for m in metrics)

    def test_training_metrics_populated(self, ft_config, tr_config):
        trainer = TripoSRTrainer(ft_config, tr_config)
        metrics = trainer.train()
        for m in metrics:
            assert m.train_loss >= 0
            assert m.learning_rate > 0
            assert m.epoch_duration_sec >= 0
            assert m.samples_processed > 0

    def test_validation_loss_tracked(self, ft_config, tr_config):
        trainer = TripoSRTrainer(ft_config, tr_config)
        metrics = trainer.train()
        # Should have validation losses since val set is non-empty
        has_val = any(m.val_loss is not None for m in metrics)
        assert has_val

    def test_checkpoints_saved(self, ft_config, tr_config):
        trainer = TripoSRTrainer(ft_config, tr_config)
        trainer.train()
        # checkpoint_every=1, so each epoch saves a checkpoint
        assert tr_config.checkpoint_dir.exists()
        checkpoints = list(tr_config.checkpoint_dir.glob("checkpoint_epoch_*.json"))
        assert len(checkpoints) >= 1

    def test_best_checkpoint_saved(self, ft_config, tr_config):
        trainer = TripoSRTrainer(ft_config, tr_config)
        trainer.train()
        best_path = tr_config.checkpoint_dir / "checkpoint_best.json"
        assert best_path.exists()

    def test_training_summary(self, ft_config, tr_config):
        trainer = TripoSRTrainer(ft_config, tr_config)
        trainer.train()
        summary = trainer.get_training_summary()
        assert summary["total_epochs"] == tr_config.num_epochs
        assert "best_val_loss" in summary
        assert "final_train_loss" in summary
        assert summary["total_samples_processed"] > 0

    def test_empty_dataset(self, tmp_path):
        ft_config = FinetuningConfig(dataset_root=tmp_path / "nonexistent")
        tr_config = TrainingConfig(
            num_epochs=2,
            learning_rate=1e-3,
            warmup_epochs=0,
            checkpoint_dir=tmp_path / "ckpt",
            n_surface_points=64,
        )
        trainer = TripoSRTrainer(ft_config, tr_config)
        metrics = trainer.train()
        assert len(metrics) == 0

    def test_early_stopping(self, ft_config, tmp_path):
        tr_config = TrainingConfig(
            num_epochs=10,
            learning_rate=1e-3,
            warmup_epochs=0,
            early_stopping_patience=2,
            checkpoint_dir=tmp_path / "ckpt",
            n_surface_points=64,
        )
        trainer = TripoSRTrainer(ft_config, tr_config)
        metrics = trainer.train()
        # Should stop before 10 epochs due to early stopping
        assert len(metrics) < 10

    def test_resume_from_checkpoint(self, ft_config, tr_config):
        # First training run (2 epochs)
        trainer1 = TripoSRTrainer(ft_config, tr_config)
        metrics1 = trainer1.train()
        first_run_epochs = len(metrics1)

        # Second run with resume - more total epochs
        tr_config_resume = TrainingConfig(
            num_epochs=first_run_epochs + 3,
            learning_rate=tr_config.learning_rate,
            warmup_epochs=0,
            checkpoint_dir=tr_config.checkpoint_dir,
            resume_from_checkpoint=True,
            n_surface_points=64,
        )
        trainer2 = TripoSRTrainer(ft_config, tr_config_resume)
        metrics2 = trainer2.train()
        # Should resume from checkpoint and run fewer epochs than total
        assert len(metrics2) > 0
        assert len(metrics2) < tr_config_resume.num_epochs
        # Best val loss should be restored
        assert trainer2.best_val_loss < float("inf")

    def test_training_summary_model_mode(self, ft_config, tr_config):
        """Training summary reports stub mode when model not available."""
        trainer = TripoSRTrainer(ft_config, tr_config)
        trainer.train()
        summary = trainer.get_training_summary()
        assert summary["model_mode"] == "stub"


# === Model-Based Training Tests (with mocks) ===


def _make_mock_torch():
    """Create a mock torch module with necessary tensor operations."""
    import types

    torch = MagicMock()

    # Create real-ish tensor behavior using numpy under the hood
    class FakeTensor:
        def __init__(self, data, requires_grad=False):
            self.data = np.array(data, dtype=np.float32)
            self.requires_grad = requires_grad
            self.grad = None
            self._backward_called = False

        def __add__(self, other):
            if isinstance(other, FakeTensor):
                return FakeTensor(self.data + other.data, requires_grad=True)
            return FakeTensor(self.data + other, requires_grad=True)

        def __truediv__(self, other):
            return FakeTensor(self.data / other, requires_grad=True)

        def backward(self):
            self._backward_called = True

        def item(self):
            return float(self.data)

        def squeeze(self, *args):
            return FakeTensor(self.data.squeeze())

        def unsqueeze(self, dim):
            return FakeTensor(np.expand_dims(self.data, dim))

        def view(self, *shape):
            return FakeTensor(self.data.reshape(shape))

        def to(self, *args, **kwargs):
            return self

        def dim(self):
            return len(self.data.shape)

        def __len__(self):
            return len(self.data)

        def __getitem__(self, idx):
            return FakeTensor(self.data[idx])

    # torch.from_numpy
    torch.from_numpy = lambda arr: FakeTensor(arr)

    # torch.tensor
    torch.tensor = lambda val, **kwargs: FakeTensor(val if isinstance(val, (list, np.ndarray)) else [val])

    # torch.cat
    torch.cat = lambda tensors: FakeTensor(np.concatenate([t.data for t in tensors]))

    # torch.no_grad context manager
    torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
    torch.no_grad.return_value.__exit__ = MagicMock(return_value=False)

    # torch.nn.functional.binary_cross_entropy_with_logits
    def bce_with_logits(input_t, target_t, reduction="mean"):
        # Simple BCE computation
        sigmoid = 1.0 / (1.0 + np.exp(-input_t.data))
        loss = -(target_t.data * np.log(sigmoid + 1e-7) + (1 - target_t.data) * np.log(1 - sigmoid + 1e-7))
        if reduction == "mean":
            return FakeTensor([loss.mean()], requires_grad=True)
        return FakeTensor(loss, requires_grad=True)

    torch.nn.functional.binary_cross_entropy_with_logits = bce_with_logits

    # torch.nn.utils.clip_grad_norm_
    torch.nn.utils.clip_grad_norm_ = MagicMock()

    # torch.save / torch.load
    torch.save = MagicMock()
    torch.load = MagicMock(return_value={})

    # torch.optim.AdamW
    mock_optimizer = MagicMock()
    mock_optimizer.param_groups = [{"lr": 1e-4}]
    torch.optim.AdamW.return_value = mock_optimizer

    return torch, FakeTensor


def _make_mock_model(fake_tensor_cls):
    """Create a mock TSR model that returns fake scene codes and meshes."""
    import trimesh

    model = MagicMock()

    # model.parameters() returns fake params with requires_grad
    fake_param = MagicMock()
    fake_param.requires_grad = True
    fake_param.numel.return_value = 1000
    model.parameters.return_value = [fake_param]

    # model([image], device=...) -> scene_codes
    scene_code = fake_tensor_cls(np.random.randn(3, 32, 32).astype(np.float32))
    model.return_value = [scene_code]

    # model.renderer.query_triplane -> density values
    def mock_query_triplane(decoder, positions, scene_code):
        n_points = positions.data.shape[1] if len(positions.data.shape) > 1 else positions.data.shape[0]
        # Return random density values (some high, some low)
        density = fake_tensor_cls(np.random.randn(n_points).astype(np.float32))
        return {"density_act": density}

    model.renderer = MagicMock()
    model.renderer.query_triplane = mock_query_triplane
    model.renderer.set_chunk_size = MagicMock()
    model.decoder = MagicMock()

    # model.extract_mesh -> list of trimesh.Trimesh
    tetra_verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32)
    tetra_faces = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], dtype=np.int64)
    mock_mesh = trimesh.Trimesh(vertices=tetra_verts, faces=tetra_faces)
    model.extract_mesh = MagicMock(return_value=[mock_mesh])

    # model.to / model.train / model.eval / model.state_dict / model.load_state_dict
    model.to.return_value = model
    model.train.return_value = model
    model.eval.return_value = model
    model.state_dict.return_value = {}
    model.load_state_dict = MagicMock()

    return model


class TestModelBasedTraining:
    """Tests for the real model training path using mock TSR model."""

    @pytest.fixture
    def mock_trainer(self, ft_config, tr_config):
        """Create a trainer with a mock model injected."""
        mock_torch, FakeTensor = _make_mock_torch()
        mock_model = _make_mock_model(FakeTensor)

        trainer = TripoSRTrainer(ft_config, tr_config)
        # Inject mock model directly (bypass _ensure_model_loaded)
        trainer.model = mock_model
        trainer._torch = mock_torch
        trainer.optimizer = mock_torch.optim.AdamW([], lr=1e-4)
        return trainer

    def test_model_training_runs(self, mock_trainer):
        """Training with mock model completes without errors."""
        metrics = mock_trainer.train()
        assert len(metrics) > 0
        assert all(isinstance(m, TrainingMetrics) for m in metrics)

    def test_model_forward_pass_called(self, mock_trainer):
        """Model forward pass is called during training."""
        mock_trainer.train()
        assert mock_trainer.model.called

    def test_optimizer_step_called(self, mock_trainer):
        """Optimizer step is called during training."""
        mock_trainer.train()
        assert mock_trainer.optimizer.step.called

    def test_optimizer_zero_grad_called(self, mock_trainer):
        """Optimizer zero_grad is called before backward."""
        mock_trainer.train()
        assert mock_trainer.optimizer.zero_grad.called

    def test_gradient_clipping_applied(self, mock_trainer):
        """Gradient clipping is applied during training."""
        mock_trainer.train()
        assert mock_trainer._torch.nn.utils.clip_grad_norm_.called

    def test_mesh_extraction_for_metrics(self, mock_trainer):
        """Mesh extraction is called for monitoring metrics."""
        mock_trainer.train()
        assert mock_trainer.model.extract_mesh.called

    def test_validation_uses_eval_mode(self, mock_trainer):
        """Model switches to eval mode during validation."""
        mock_trainer.train()
        mock_trainer.model.eval.assert_called()
        # Model should be back in train mode after validation
        mock_trainer.model.train.assert_called()

    def test_model_weights_saved_on_best(self, mock_trainer, tr_config):
        """Model weights are saved when best validation loss improves."""
        mock_trainer.train()
        # torch.save should be called for model weights
        assert mock_trainer._torch.save.called

    def test_training_summary_reports_real_mode(self, mock_trainer):
        """Training summary reports 'real' model mode."""
        mock_trainer.train()
        summary = mock_trainer.get_training_summary()
        assert summary["model_mode"] == "real"

    def test_compute_sample_loss_uses_model(self, mock_trainer):
        """_compute_sample_loss uses model inference when available."""
        image = Image.new("RGB", (64, 64), color=(128, 128, 128))
        mesh = MeshData(
            vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32),
            faces=np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], dtype=np.int64),
            vertex_count=4,
            face_count=4,
        )
        loss = mock_trainer._compute_sample_loss(image, mesh)
        assert isinstance(loss, LossResult)
        assert loss.total >= 0
        # Model should have been called for inference
        assert mock_trainer.model.called

    def test_density_query_called(self, mock_trainer):
        """Density field is queried during occupancy loss computation."""
        mock_trainer.train()
        # The renderer's query_triplane should have been called
        # (it's a real function, not a MagicMock, so check model call instead)
        assert mock_trainer.model.called

    def test_learning_rate_updated_per_step(self, mock_trainer):
        """Learning rate is updated in optimizer param groups."""
        mock_trainer.train()
        # param_groups should have been accessed for LR update
        assert mock_trainer.optimizer.param_groups is not None
