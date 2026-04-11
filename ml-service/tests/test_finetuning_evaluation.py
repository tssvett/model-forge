"""Tests for fine-tuning evaluation module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import trimesh
from PIL import Image

from modelforge.finetuning.config import FinetuningConfig
from modelforge.finetuning.dataset import DataSample
from modelforge.finetuning.evaluation import (
    EvaluationReport,
    FinetuningEvaluator,
    SampleEvaluation,
)


# === Helpers ===


def _make_tetrahedron(offset=0.0):
    """Create a simple tetrahedron mesh with optional vertex offset."""
    vertices = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64
    ) + offset
    faces = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], dtype=np.int64)
    return trimesh.Trimesh(vertices=vertices, faces=faces)


def _make_cube(offset=0.0):
    """Create a simple cube mesh with optional vertex offset."""
    vertices = np.array(
        [
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
        ],
        dtype=np.float64,
    ) + offset
    faces = np.array(
        [
            [0, 1, 2], [0, 2, 3],
            [4, 5, 6], [4, 6, 7],
            [0, 1, 5], [0, 5, 4],
            [2, 3, 7], [2, 7, 6],
            [0, 3, 7], [0, 7, 4],
            [1, 2, 6], [1, 6, 5],
        ],
        dtype=np.int64,
    )
    return trimesh.Trimesh(vertices=vertices, faces=faces)


@pytest.fixture
def ft_config(tmp_path):
    return FinetuningConfig(
        dataset_root=tmp_path,
        dataset_type="shapenet",
        seed=42,
    )


@pytest.fixture
def evaluator(ft_config):
    return FinetuningEvaluator(
        finetuning_config=ft_config,
        num_surface_samples=500,
        voxel_resolution=16,
        f_score_threshold=0.01,
    )


# === SampleEvaluation tests ===


class TestSampleEvaluation:
    def test_has_both_true(self):
        ev = SampleEvaluation(
            sample_id="s1",
            category="chair",
            base_metrics={"chamfer_distance": 0.01},
            finetuned_metrics={"chamfer_distance": 0.005},
        )
        assert ev.has_both() is True

    def test_has_both_false_missing_base(self):
        ev = SampleEvaluation(
            sample_id="s1",
            category="chair",
            finetuned_metrics={"chamfer_distance": 0.005},
        )
        assert ev.has_both() is False

    def test_has_both_false_missing_finetuned(self):
        ev = SampleEvaluation(
            sample_id="s1",
            category="chair",
            base_metrics={"chamfer_distance": 0.01},
        )
        assert ev.has_both() is False

    def test_has_both_false_neither(self):
        ev = SampleEvaluation(sample_id="s1", category="chair")
        assert ev.has_both() is False


# === EvaluationReport tests ===


class TestEvaluationReport:
    def _make_report(self):
        return EvaluationReport(
            base_version="base_v1",
            finetuned_version="ft_v1",
            dataset_type="shapenet",
            num_samples=10,
            num_evaluated=8,
            base_mean_metrics={
                "chamfer_distance": 0.05,
                "iou_3d": 0.6,
                "f_score": 0.7,
                "normal_consistency": 0.8,
            },
            finetuned_mean_metrics={
                "chamfer_distance": 0.03,
                "iou_3d": 0.75,
                "f_score": 0.85,
                "normal_consistency": 0.9,
            },
            improvements={
                "chamfer_distance": 0.02,
                "iou_3d": 0.15,
                "f_score": 0.15,
                "normal_consistency": 0.1,
            },
            improvement_percentages={
                "chamfer_distance": 40.0,
                "iou_3d": 25.0,
                "f_score": 21.4,
                "normal_consistency": 12.5,
            },
            category_metrics={
                "chair": {
                    "base_chamfer_distance": 0.04,
                    "finetuned_chamfer_distance": 0.02,
                    "count": 5,
                }
            },
        )

    def test_to_dict_contains_all_fields(self):
        report = self._make_report()
        d = report.to_dict()
        assert d["base_version"] == "base_v1"
        assert d["finetuned_version"] == "ft_v1"
        assert d["dataset_type"] == "shapenet"
        assert d["num_samples"] == 10
        assert d["num_evaluated"] == 8
        assert "chamfer_distance" in d["base_mean_metrics"]
        assert "chamfer_distance" in d["improvements"]
        assert "chair" in d["category_metrics"]

    def test_save_and_load(self, tmp_path):
        report = self._make_report()
        path = tmp_path / "reports" / "eval.json"
        report.save(path)

        assert path.exists()
        loaded = EvaluationReport.load(path)
        assert loaded.base_version == report.base_version
        assert loaded.finetuned_version == report.finetuned_version
        assert loaded.num_samples == report.num_samples
        assert loaded.num_evaluated == report.num_evaluated
        assert loaded.base_mean_metrics == report.base_mean_metrics
        assert loaded.finetuned_mean_metrics == report.finetuned_mean_metrics
        assert loaded.improvements == report.improvements
        assert loaded.improvement_percentages == report.improvement_percentages

    def test_save_creates_parent_dirs(self, tmp_path):
        report = self._make_report()
        path = tmp_path / "a" / "b" / "c" / "report.json"
        report.save(path)
        assert path.exists()

    def test_summary_format(self):
        report = self._make_report()
        summary = report.summary()
        assert "base_v1" in summary
        assert "ft_v1" in summary
        assert "Chamfer Distance" in summary
        assert "IoU 3D" in summary
        assert "F-Score" in summary
        assert "Normal Consistency" in summary
        assert "chair" in summary

    def test_summary_empty_report(self):
        report = EvaluationReport(
            base_version="base",
            finetuned_version="ft",
            dataset_type="shapenet",
            num_samples=0,
            num_evaluated=0,
        )
        summary = report.summary()
        assert "N/A" in summary


# === FinetuningEvaluator tests ===


class TestFinetuningEvaluator:
    def test_evaluate_meshes_identical(self, evaluator):
        """Identical meshes should have ~0 chamfer distance and high IoU."""
        mesh = _make_tetrahedron()
        metrics = evaluator.evaluate_meshes(mesh, mesh)

        md = metrics.to_dict()
        # With surface sampling, identical meshes have small but non-zero chamfer
        assert md["chamfer_distance"] < 0.01
        assert md["iou_3d"] > 0.5
        assert md["f_score"] > 0.0  # F-score depends on threshold vs mesh scale

    def test_evaluate_meshes_different(self, evaluator):
        """Offset meshes should have positive chamfer distance."""
        gt = _make_tetrahedron()
        pred = _make_tetrahedron(offset=0.5)
        metrics = evaluator.evaluate_meshes(pred, gt)

        md = metrics.to_dict()
        assert md["chamfer_distance"] > 0.01

    def test_evaluate_dataset_basic(self, evaluator):
        """Full dataset evaluation pipeline with 2 samples."""
        gt1 = _make_tetrahedron()
        gt2 = _make_cube()

        # Base: more noise
        base1 = _make_tetrahedron(offset=0.05)
        base2 = _make_cube(offset=0.05)

        # Fine-tuned: less noise (closer to GT)
        ft1 = _make_tetrahedron(offset=0.01)
        ft2 = _make_cube(offset=0.01)

        ground_truths = {"s1": gt1, "s2": gt2}
        base_preds = {"s1": base1, "s2": base2}
        ft_preds = {"s1": ft1, "s2": ft2}
        metadata = {
            "s1": DataSample(image_path=Path("a.png"), mesh_path=Path("a.obj"), category="chair", model_id="s1", metadata={}),
            "s2": DataSample(image_path=Path("b.png"), mesh_path=Path("b.obj"), category="table", model_id="s2", metadata={}),
        }

        report = evaluator.evaluate_dataset(
            base_predictions=base_preds,
            finetuned_predictions=ft_preds,
            ground_truths=ground_truths,
            sample_metadata=metadata,
        )

        assert report.num_samples == 2
        assert report.num_evaluated == 2
        assert report.dataset_type == "shapenet"
        assert len(report.sample_evaluations) == 2

        # Fine-tuned should have lower chamfer distance
        assert report.finetuned_mean_metrics["chamfer_distance"] < report.base_mean_metrics["chamfer_distance"]
        # Positive improvement for chamfer (lower-is-better, negated)
        assert report.improvements["chamfer_distance"] > 0

    def test_evaluate_dataset_missing_predictions(self, evaluator):
        """Samples missing from predictions should not count as evaluated."""
        gt = _make_tetrahedron()
        base = _make_tetrahedron(offset=0.05)
        ft = _make_tetrahedron(offset=0.01)

        report = evaluator.evaluate_dataset(
            base_predictions={"s1": base},
            finetuned_predictions={"s1": ft},
            ground_truths={"s1": gt, "s2": _make_cube()},
            sample_metadata={},
        )

        assert report.num_samples == 2
        # Only s1 has both predictions
        assert report.num_evaluated == 1

    def test_evaluate_dataset_per_category_metrics(self, evaluator):
        """Category breakdowns should be populated correctly."""
        gt = _make_tetrahedron()
        base = _make_tetrahedron(offset=0.05)
        ft = _make_tetrahedron(offset=0.01)

        metadata = {
            "s1": DataSample(image_path=Path("a.png"), mesh_path=Path("a.obj"), category="chair", model_id="s1", metadata={}),
        }

        report = evaluator.evaluate_dataset(
            base_predictions={"s1": base},
            finetuned_predictions={"s1": ft},
            ground_truths={"s1": gt},
            sample_metadata=metadata,
        )

        assert "chair" in report.category_metrics
        assert report.category_metrics["chair"]["count"] == 1
        assert "base_chamfer_distance" in report.category_metrics["chair"]
        assert "finetuned_chamfer_distance" in report.category_metrics["chair"]

    def test_simulate_base_prediction(self):
        """Base simulation should add noise to mesh vertices."""
        gt = _make_tetrahedron()
        base = FinetuningEvaluator._simulate_base_prediction(gt)
        assert base.vertices.shape == gt.vertices.shape
        assert not np.allclose(base.vertices, gt.vertices)

    def test_simulate_finetuned_prediction(self):
        """Fine-tuned simulation should add less noise than base."""
        gt = _make_tetrahedron()
        base = FinetuningEvaluator._simulate_base_prediction(gt)
        ft = FinetuningEvaluator._simulate_finetuned_prediction(gt)

        base_diff = np.mean(np.abs(base.vertices - gt.vertices))
        ft_diff = np.mean(np.abs(ft.vertices - gt.vertices))
        assert ft_diff < base_diff

    def test_build_report_empty(self, evaluator):
        """Empty evaluations should produce a valid report with zero metrics."""
        report = evaluator._build_report(
            evaluations=[],
            base_version="base",
            finetuned_version="ft",
            dataset_type="shapenet",
            total_samples=0,
        )
        assert report.num_evaluated == 0
        assert report.base_mean_metrics == {}
        assert report.improvements == {}

    def test_improvement_direction_lower_is_better(self, evaluator):
        """Chamfer distance improvement should be positive when finetuned < base."""
        ev = SampleEvaluation(
            sample_id="s1",
            category="chair",
            base_metrics={"chamfer_distance": 0.1, "iou_3d": 0.5, "f_score": 0.6, "normal_consistency": 0.7},
            finetuned_metrics={"chamfer_distance": 0.05, "iou_3d": 0.7, "f_score": 0.8, "normal_consistency": 0.85},
        )

        report = evaluator._build_report(
            evaluations=[ev],
            base_version="base",
            finetuned_version="ft",
            dataset_type="shapenet",
            total_samples=1,
        )

        # Chamfer: lower is better, so improvement = base - finetuned > 0
        assert report.improvements["chamfer_distance"] > 0
        assert report.improvement_percentages["chamfer_distance"] > 0

        # IoU/F-Score/NC: higher is better, so improvement = finetuned - base > 0
        assert report.improvements["iou_3d"] > 0
        assert report.improvements["f_score"] > 0
        assert report.improvements["normal_consistency"] > 0


# === Model-Based Evaluation Tests ===


def _make_mock_model():
    """Create a mock TSR model that returns trimesh objects."""
    model = MagicMock()

    # model.parameters()
    fake_param = MagicMock()
    fake_param.numel.return_value = 1000
    model.parameters.return_value = [fake_param]

    # model([image], device=...) -> scene_codes
    scene_code = MagicMock()
    model.return_value = [scene_code]

    # model.extract_mesh -> list of trimesh.Trimesh
    tetra_verts = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32,
    )
    tetra_faces = np.array(
        [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], dtype=np.int64,
    )
    mock_mesh = trimesh.Trimesh(vertices=tetra_verts, faces=tetra_faces)
    model.extract_mesh = MagicMock(return_value=[mock_mesh])

    model.renderer = MagicMock()
    model.renderer.set_chunk_size = MagicMock()
    model.to.return_value = model
    model.eval.return_value = model
    model.train.return_value = model
    model.state_dict.return_value = {}
    model.load_state_dict = MagicMock()

    return model


class TestModelBasedEvaluation:
    """Tests for evaluation with mock TripoSR model."""

    @pytest.fixture
    def mock_evaluator(self, ft_config):
        """Create an evaluator with mock model injected."""
        mock_torch = MagicMock()
        mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
        mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=False)
        mock_torch.load = MagicMock(return_value={})

        evaluator = FinetuningEvaluator(
            finetuning_config=ft_config,
            num_surface_samples=500,
            voxel_resolution=16,
        )
        evaluator._model = _make_mock_model()
        evaluator._torch = mock_torch
        return evaluator

    def test_predict_mesh_returns_trimesh(self, mock_evaluator):
        """_predict_mesh returns a trimesh when model is loaded."""
        image = Image.new("RGB", (64, 64), color=(128, 128, 128))
        mesh = mock_evaluator._predict_mesh(image)
        assert isinstance(mesh, trimesh.Trimesh)
        assert len(mesh.vertices) > 0

    def test_predict_mesh_calls_model(self, mock_evaluator):
        """_predict_mesh calls the model for inference."""
        image = Image.new("RGB", (64, 64), color=(128, 128, 128))
        mock_evaluator._predict_mesh(image)
        assert mock_evaluator._model.called

    def test_predict_mesh_calls_extract_mesh(self, mock_evaluator):
        """_predict_mesh calls extract_mesh for mesh generation."""
        image = Image.new("RGB", (64, 64), color=(128, 128, 128))
        mock_evaluator._predict_mesh(image)
        assert mock_evaluator._model.extract_mesh.called

    def test_predict_mesh_returns_none_without_model(self, ft_config):
        """_predict_mesh returns None when no model is loaded."""
        evaluator = FinetuningEvaluator(finetuning_config=ft_config)
        image = Image.new("RGB", (64, 64))
        assert evaluator._predict_mesh(image) is None

    def test_load_finetuned_weights(self, mock_evaluator, tmp_path):
        """Fine-tuned weights can be loaded into the model."""
        weights_path = tmp_path / "weights.pt"
        weights_path.touch()
        result = mock_evaluator._load_finetuned_weights(weights_path)
        assert result is True
        mock_evaluator._model.load_state_dict.assert_called()

    def test_load_finetuned_weights_no_model(self, ft_config, tmp_path):
        """Loading weights without model returns False."""
        evaluator = FinetuningEvaluator(finetuning_config=ft_config)
        weights_path = tmp_path / "weights.pt"
        weights_path.touch()
        assert evaluator._load_finetuned_weights(weights_path) is False

    def test_evaluate_from_test_split_with_model(self, mock_evaluator, tmp_path):
        """evaluate_from_test_split uses model inference when available."""
        # Create minimal dataset
        cat_dir = tmp_path / "chair" / "model_000"
        images_dir = cat_dir / "images"
        images_dir.mkdir(parents=True)
        Image.new("RGB", (64, 64), color=(100, 150, 200)).save(images_dir / "000.png")
        with open(cat_dir / "model.obj", "w") as f:
            f.write("v 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nv 0.0 0.0 1.0\n")
            f.write("f 1 2 3\nf 1 2 4\nf 1 3 4\nf 2 3 4\n")

        mock_evaluator.ft_config = FinetuningConfig(
            dataset_root=tmp_path,
            train_ratio=0.0,
            val_ratio=0.0,
            test_ratio=1.0,
            seed=42,
        )

        report = mock_evaluator.evaluate_from_test_split()

        assert report.num_samples > 0
        assert mock_evaluator._model.called

    def test_evaluate_from_test_split_with_finetuned_weights(
        self, mock_evaluator, tmp_path,
    ):
        """evaluate_from_test_split loads fine-tuned weights when path provided."""
        # Create minimal dataset
        cat_dir = tmp_path / "chair" / "model_000"
        images_dir = cat_dir / "images"
        images_dir.mkdir(parents=True)
        Image.new("RGB", (64, 64), color=(100, 150, 200)).save(images_dir / "000.png")
        with open(cat_dir / "model.obj", "w") as f:
            f.write("v 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nv 0.0 0.0 1.0\n")
            f.write("f 1 2 3\nf 1 2 4\nf 1 3 4\nf 2 3 4\n")

        weights_path = tmp_path / "model_weights.pt"
        weights_path.touch()

        mock_evaluator.ft_config = FinetuningConfig(
            dataset_root=tmp_path,
            train_ratio=0.0,
            val_ratio=0.0,
            test_ratio=1.0,
            seed=42,
        )

        report = mock_evaluator.evaluate_from_test_split(
            finetuned_weights_path=weights_path,
        )

        assert report.num_samples > 0
        # Model should have been called for both base and fine-tuned inference
        assert mock_evaluator._model.call_count >= 2
        # Weights should have been loaded
        mock_evaluator._model.load_state_dict.assert_called()

    def test_simulation_fallback_without_model(self, tmp_path):
        """Without model, evaluate_from_test_split falls back to simulation."""
        # Create minimal dataset
        cat_dir = tmp_path / "chair" / "model_000"
        images_dir = cat_dir / "images"
        images_dir.mkdir(parents=True)
        Image.new("RGB", (64, 64), color=(100, 150, 200)).save(images_dir / "000.png")
        with open(cat_dir / "model.obj", "w") as f:
            f.write("v 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nv 0.0 0.0 1.0\n")
            f.write("f 1 2 3\nf 1 2 4\nf 1 3 4\nf 2 3 4\n")

        ft_config = FinetuningConfig(
            dataset_root=tmp_path,
            train_ratio=0.0,
            val_ratio=0.0,
            test_ratio=1.0,
            seed=42,
        )
        evaluator = FinetuningEvaluator(
            finetuning_config=ft_config,
            num_surface_samples=500,
            voxel_resolution=16,
        )

        report = evaluator.evaluate_from_test_split()

        assert report.num_samples > 0
        assert report.num_evaluated > 0
        # Both model versions should have metrics
        assert len(report.base_mean_metrics) > 0
        assert len(report.finetuned_mean_metrics) > 0
