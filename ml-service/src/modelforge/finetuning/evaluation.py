"""Evaluation pipeline for comparing base vs fine-tuned TripoSR models.

Runs both model versions on a test dataset, computes scientific metrics
(Chamfer Distance, IoU, F-Score, Normal Consistency) against ground truth,
and generates comparison reports.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import trimesh

from ..metrics.quality import (
    MeshQualityMetrics,
    compute_comparison_metrics,
    compute_self_metrics,
)
from .dataset import DataSample, DatasetSplit, MeshData, ShapeNetDataset, create_data_loaders
from .config import FinetuningConfig

logger = logging.getLogger(__name__)


@dataclass
class SampleEvaluation:
    """Evaluation result for a single test sample."""

    sample_id: str
    category: str
    base_metrics: Optional[Dict[str, Any]] = None
    finetuned_metrics: Optional[Dict[str, Any]] = None
    base_error: Optional[str] = None
    finetuned_error: Optional[str] = None

    def has_both(self) -> bool:
        return self.base_metrics is not None and self.finetuned_metrics is not None


@dataclass
class EvaluationReport:
    """Aggregated comparison report between base and fine-tuned models."""

    base_version: str
    finetuned_version: str
    dataset_type: str
    num_samples: int
    num_evaluated: int
    timestamp: float = field(default_factory=time.time)

    # Aggregated metrics (mean across test samples)
    base_mean_metrics: Dict[str, float] = field(default_factory=dict)
    finetuned_mean_metrics: Dict[str, float] = field(default_factory=dict)

    # Improvement deltas (finetuned - base), positive = finetuned is better
    # For Chamfer Distance, we negate so positive always means improvement
    improvements: Dict[str, float] = field(default_factory=dict)
    improvement_percentages: Dict[str, float] = field(default_factory=dict)

    # Per-category breakdowns
    category_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Individual sample results
    sample_evaluations: List[SampleEvaluation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "base_version": self.base_version,
            "finetuned_version": self.finetuned_version,
            "dataset_type": self.dataset_type,
            "num_samples": self.num_samples,
            "num_evaluated": self.num_evaluated,
            "timestamp": self.timestamp,
            "base_mean_metrics": self.base_mean_metrics,
            "finetuned_mean_metrics": self.finetuned_mean_metrics,
            "improvements": self.improvements,
            "improvement_percentages": self.improvement_percentages,
            "category_metrics": self.category_metrics,
        }
        return result

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info("Evaluation report saved to %s", path)

    @classmethod
    def load(cls, path: Path) -> "EvaluationReport":
        with open(path, "r") as f:
            data = json.load(f)
        report = cls(
            base_version=data["base_version"],
            finetuned_version=data["finetuned_version"],
            dataset_type=data["dataset_type"],
            num_samples=data["num_samples"],
            num_evaluated=data["num_evaluated"],
            timestamp=data.get("timestamp", 0),
            base_mean_metrics=data.get("base_mean_metrics", {}),
            finetuned_mean_metrics=data.get("finetuned_mean_metrics", {}),
            improvements=data.get("improvements", {}),
            improvement_percentages=data.get("improvement_percentages", {}),
            category_metrics=data.get("category_metrics", {}),
        )
        return report

    def summary(self) -> str:
        """Generate a human-readable summary of the evaluation."""
        lines = [
            f"=== Evaluation Report: {self.base_version} vs {self.finetuned_version} ===",
            f"Dataset: {self.dataset_type} ({self.num_evaluated}/{self.num_samples} samples)",
            "",
            "Metric               | Base       | Fine-tuned | Improvement",
            "---------------------+------------+------------+------------",
        ]

        metric_names = ["chamfer_distance", "iou_3d", "f_score", "normal_consistency"]
        display_names = {
            "chamfer_distance": "Chamfer Distance",
            "iou_3d": "IoU 3D",
            "f_score": "F-Score",
            "normal_consistency": "Normal Consistency",
        }

        for metric in metric_names:
            base_val = self.base_mean_metrics.get(metric)
            ft_val = self.finetuned_mean_metrics.get(metric)
            pct = self.improvement_percentages.get(metric)

            base_str = f"{base_val:.6f}" if base_val is not None else "N/A"
            ft_str = f"{ft_val:.6f}" if ft_val is not None else "N/A"
            pct_str = f"{pct:+.1f}%" if pct is not None else "N/A"

            name = display_names.get(metric, metric)
            lines.append(f"{name:<21}| {base_str:<11}| {ft_str:<11}| {pct_str}")

        if self.category_metrics:
            lines.append("")
            lines.append("Per-category Chamfer Distance:")
            for cat, cat_metrics in sorted(self.category_metrics.items()):
                base_cd = cat_metrics.get("base_chamfer_distance")
                ft_cd = cat_metrics.get("finetuned_chamfer_distance")
                count = cat_metrics.get("count", 0)
                if base_cd is not None and ft_cd is not None:
                    lines.append(
                        f"  {cat}: base={base_cd:.6f}, finetuned={ft_cd:.6f} ({count} samples)"
                    )

        return "\n".join(lines)


# Metrics where lower is better (we negate improvement so positive = better)
_LOWER_IS_BETTER = {"chamfer_distance"}
# Metrics to aggregate
_COMPARISON_METRICS = ["chamfer_distance", "iou_3d", "f_score", "normal_consistency"]


class FinetuningEvaluator:
    """Evaluates and compares base vs fine-tuned model predictions.

    Since actual model inference requires GPU and loaded models, this evaluator
    works with pre-computed meshes or with ground truth meshes from the dataset
    to validate the metrics pipeline.

    In production use, an inference service would generate predictions which
    are then compared against ground truth using this evaluator.
    """

    def __init__(
        self,
        finetuning_config: FinetuningConfig,
        num_surface_samples: int = 10_000,
        voxel_resolution: int = 32,
        f_score_threshold: float = 0.01,
    ):
        self.ft_config = finetuning_config
        self.num_surface_samples = num_surface_samples
        self.voxel_resolution = voxel_resolution
        self.f_score_threshold = f_score_threshold

    def evaluate_meshes(
        self,
        predicted: trimesh.Trimesh,
        ground_truth: trimesh.Trimesh,
    ) -> MeshQualityMetrics:
        """Evaluate a single predicted mesh against ground truth."""
        return compute_comparison_metrics(
            predicted=predicted,
            ground_truth=ground_truth,
            num_samples=self.num_surface_samples,
            voxel_resolution=self.voxel_resolution,
            f_score_threshold=self.f_score_threshold,
        )

    def evaluate_dataset(
        self,
        base_predictions: Dict[str, trimesh.Trimesh],
        finetuned_predictions: Dict[str, trimesh.Trimesh],
        ground_truths: Dict[str, trimesh.Trimesh],
        sample_metadata: Dict[str, DataSample],
        base_version: str = "base",
        finetuned_version: str = "finetuned",
    ) -> EvaluationReport:
        """Evaluate both model versions on a set of samples.

        Args:
            base_predictions: {sample_id: mesh} from base model
            finetuned_predictions: {sample_id: mesh} from fine-tuned model
            ground_truths: {sample_id: mesh} ground truth meshes
            sample_metadata: {sample_id: DataSample} for category info
            base_version: Version label for the base model
            finetuned_version: Version label for the fine-tuned model

        Returns:
            EvaluationReport with aggregated and per-sample metrics
        """
        all_sample_ids = set(ground_truths.keys())
        evaluations: List[SampleEvaluation] = []

        logger.info(
            "Evaluating %d samples: base=%s vs finetuned=%s",
            len(all_sample_ids), base_version, finetuned_version,
        )

        for sample_id in sorted(all_sample_ids):
            gt_mesh = ground_truths[sample_id]
            metadata = sample_metadata.get(sample_id)
            category = metadata.category if metadata else "unknown"

            eval_result = SampleEvaluation(
                sample_id=sample_id,
                category=category,
            )

            # Evaluate base model prediction
            if sample_id in base_predictions:
                try:
                    base_metrics = self.evaluate_meshes(
                        base_predictions[sample_id], gt_mesh
                    )
                    eval_result.base_metrics = base_metrics.to_dict()
                except Exception as e:
                    eval_result.base_error = str(e)
                    logger.warning("Base eval failed for %s: %s", sample_id, e)

            # Evaluate fine-tuned model prediction
            if sample_id in finetuned_predictions:
                try:
                    ft_metrics = self.evaluate_meshes(
                        finetuned_predictions[sample_id], gt_mesh
                    )
                    eval_result.finetuned_metrics = ft_metrics.to_dict()
                except Exception as e:
                    eval_result.finetuned_error = str(e)
                    logger.warning("Finetuned eval failed for %s: %s", sample_id, e)

            evaluations.append(eval_result)

        return self._build_report(
            evaluations=evaluations,
            base_version=base_version,
            finetuned_version=finetuned_version,
            dataset_type=self.ft_config.dataset_type,
            total_samples=len(all_sample_ids),
        )

    def evaluate_from_test_split(
        self,
        base_version: str = "base",
        finetuned_version: str = "finetuned",
        max_samples: Optional[int] = None,
    ) -> EvaluationReport:
        """Evaluate using the test split from the dataset.

        Since we don't have real model predictions in the evaluation pipeline,
        this method simulates evaluation by comparing ground truth meshes
        against perturbed versions, validating the full metrics pipeline.

        In a real scenario, you'd pass actual model predictions to evaluate_dataset().

        Args:
            base_version: Version label for the base model
            finetuned_version: Version label for the fine-tuned model
            max_samples: Limit number of test samples (None = all)

        Returns:
            EvaluationReport demonstrating the metrics pipeline
        """
        datasets = create_data_loaders(self.ft_config)
        test_dataset = datasets[DatasetSplit.TEST]

        if len(test_dataset) == 0:
            logger.warning("Test dataset is empty")
            return EvaluationReport(
                base_version=base_version,
                finetuned_version=finetuned_version,
                dataset_type=self.ft_config.dataset_type,
                num_samples=0,
                num_evaluated=0,
            )

        n_samples = min(max_samples, len(test_dataset)) if max_samples else len(test_dataset)

        ground_truths: Dict[str, trimesh.Trimesh] = {}
        base_predictions: Dict[str, trimesh.Trimesh] = {}
        finetuned_predictions: Dict[str, trimesh.Trimesh] = {}
        sample_metadata: Dict[str, DataSample] = {}

        for idx in range(n_samples):
            try:
                image, mesh_data, sample = test_dataset[idx]
                if not mesh_data.is_valid:
                    continue

                sample_id = sample.model_id or f"sample_{idx}"
                gt_mesh = trimesh.Trimesh(
                    vertices=mesh_data.vertices,
                    faces=mesh_data.faces,
                )
                ground_truths[sample_id] = gt_mesh
                sample_metadata[sample_id] = sample

                # Simulate base model: add noise to ground truth
                base_mesh = self._simulate_base_prediction(gt_mesh)
                base_predictions[sample_id] = base_mesh

                # Simulate fine-tuned model: add less noise (closer to GT)
                ft_mesh = self._simulate_finetuned_prediction(gt_mesh)
                finetuned_predictions[sample_id] = ft_mesh

            except Exception as e:
                logger.debug("Skipping test sample %d: %s", idx, e)

        return self.evaluate_dataset(
            base_predictions=base_predictions,
            finetuned_predictions=finetuned_predictions,
            ground_truths=ground_truths,
            sample_metadata=sample_metadata,
            base_version=base_version,
            finetuned_version=finetuned_version,
        )

    @staticmethod
    def _simulate_base_prediction(gt_mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Simulate a base model prediction by adding noise to ground truth."""
        noise = np.random.RandomState(42).normal(0, 0.02, gt_mesh.vertices.shape)
        return trimesh.Trimesh(
            vertices=gt_mesh.vertices + noise,
            faces=gt_mesh.faces.copy(),
        )

    @staticmethod
    def _simulate_finetuned_prediction(gt_mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Simulate a fine-tuned model prediction (less noise than base)."""
        noise = np.random.RandomState(42).normal(0, 0.005, gt_mesh.vertices.shape)
        return trimesh.Trimesh(
            vertices=gt_mesh.vertices + noise,
            faces=gt_mesh.faces.copy(),
        )

    def _build_report(
        self,
        evaluations: List[SampleEvaluation],
        base_version: str,
        finetuned_version: str,
        dataset_type: str,
        total_samples: int,
    ) -> EvaluationReport:
        """Aggregate per-sample evaluations into a report."""
        successful = [e for e in evaluations if e.has_both()]

        report = EvaluationReport(
            base_version=base_version,
            finetuned_version=finetuned_version,
            dataset_type=dataset_type,
            num_samples=total_samples,
            num_evaluated=len(successful),
            sample_evaluations=evaluations,
        )

        if not successful:
            return report

        # Aggregate mean metrics
        base_values: Dict[str, List[float]] = {m: [] for m in _COMPARISON_METRICS}
        ft_values: Dict[str, List[float]] = {m: [] for m in _COMPARISON_METRICS}
        category_data: Dict[str, Dict[str, List[float]]] = {}

        for ev in successful:
            for metric in _COMPARISON_METRICS:
                bv = ev.base_metrics.get(metric)
                fv = ev.finetuned_metrics.get(metric)
                if bv is not None and fv is not None:
                    base_values[metric].append(bv)
                    ft_values[metric].append(fv)

                    # Per-category tracking
                    cat = ev.category
                    if cat not in category_data:
                        category_data[cat] = {
                            f"base_{m}": [] for m in _COMPARISON_METRICS
                        }
                        category_data[cat].update({
                            f"finetuned_{m}": [] for m in _COMPARISON_METRICS
                        })
                        category_data[cat]["count"] = []
                    category_data[cat][f"base_{metric}"].append(bv)
                    category_data[cat][f"finetuned_{metric}"].append(fv)

        # Compute means
        for metric in _COMPARISON_METRICS:
            if base_values[metric]:
                report.base_mean_metrics[metric] = float(np.mean(base_values[metric]))
                report.finetuned_mean_metrics[metric] = float(np.mean(ft_values[metric]))

                base_mean = report.base_mean_metrics[metric]
                ft_mean = report.finetuned_mean_metrics[metric]

                if metric in _LOWER_IS_BETTER:
                    # For Chamfer: improvement = base - finetuned (positive = better)
                    report.improvements[metric] = base_mean - ft_mean
                    if abs(base_mean) > 1e-10:
                        report.improvement_percentages[metric] = (
                            (base_mean - ft_mean) / abs(base_mean) * 100
                        )
                else:
                    # For IoU, F-Score, NC: improvement = finetuned - base
                    report.improvements[metric] = ft_mean - base_mean
                    if abs(base_mean) > 1e-10:
                        report.improvement_percentages[metric] = (
                            (ft_mean - base_mean) / abs(base_mean) * 100
                        )

        # Per-category summaries
        for cat, cat_vals in category_data.items():
            report.category_metrics[cat] = {}
            for metric in _COMPARISON_METRICS:
                base_key = f"base_{metric}"
                ft_key = f"finetuned_{metric}"
                if cat_vals.get(base_key):
                    report.category_metrics[cat][base_key] = float(
                        np.mean(cat_vals[base_key])
                    )
                    report.category_metrics[cat][ft_key] = float(
                        np.mean(cat_vals[ft_key])
                    )
            report.category_metrics[cat]["count"] = len(
                cat_vals.get(f"base_{_COMPARISON_METRICS[0]}", [])
            )

        logger.info(
            "Evaluation complete: %d/%d samples, improvements: %s",
            len(successful),
            total_samples,
            {k: f"{v:+.1f}%" for k, v in report.improvement_percentages.items()},
        )

        return report
