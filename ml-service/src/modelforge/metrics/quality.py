"""
Scientific 3D mesh quality metrics.

Computes self-metrics (no ground truth needed) and comparison metrics
(require ground truth mesh) for evaluating 3D generation quality.

Metrics:
- Chamfer Distance: average nearest-neighbor distance between point clouds
- IoU 3D: volumetric intersection-over-union via voxelization
- F-Score: harmonic mean of precision/recall at a distance threshold
- Normal Consistency: average dot product of matched surface normals
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import trimesh

logger = logging.getLogger(__name__)

# Default number of points to sample from mesh surfaces
DEFAULT_NUM_SAMPLES = 10_000
# Default voxel grid resolution for IoU computation
DEFAULT_VOXEL_RESOLUTION = 32
# Default distance threshold for F-Score (relative to bounding box diagonal)
DEFAULT_F_SCORE_THRESHOLD = 0.01


@dataclass
class MeshQualityMetrics:
    """Container for all computed mesh quality metrics."""

    # Self-metrics (always computed)
    vertices: int = 0
    faces: int = 0
    is_watertight: bool = False
    normal_consistency: Optional[float] = None

    # Comparison metrics (only when ground truth available)
    chamfer_distance: Optional[float] = None
    iou_3d: Optional[float] = None
    f_score: Optional[float] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


def compute_self_metrics(mesh: trimesh.Trimesh) -> MeshQualityMetrics:
    """
    Compute metrics that don't require ground truth.

    :param mesh: Generated 3D mesh
    :return: MeshQualityMetrics with self-metrics filled
    """
    metrics = MeshQualityMetrics(
        vertices=len(mesh.vertices),
        faces=len(mesh.faces),
        is_watertight=bool(mesh.is_watertight),
    )

    # Normal consistency: average dot product of face normals with vertex normals
    # Higher = smoother, more consistent normals
    try:
        if len(mesh.face_normals) > 0 and len(mesh.vertex_normals) > 0:
            face_normals = mesh.face_normals
            # For each face, average the vertex normals of its 3 vertices
            vertex_normals_per_face = mesh.vertex_normals[mesh.faces]  # (F, 3, 3)
            avg_vertex_normals = vertex_normals_per_face.mean(axis=1)  # (F, 3)
            # Normalize
            norms = np.linalg.norm(avg_vertex_normals, axis=1, keepdims=True)
            norms = np.clip(norms, 1e-8, None)
            avg_vertex_normals = avg_vertex_normals / norms
            # Dot product — consistency between face normals and averaged vertex normals
            dots = np.abs(np.sum(face_normals * avg_vertex_normals, axis=1))
            metrics.normal_consistency = float(np.mean(dots))
    except Exception as e:
        logger.warning("Failed to compute normal consistency: %s", e)

    return metrics


def _sample_points_and_normals(
    mesh: trimesh.Trimesh, num_samples: int
) -> tuple[np.ndarray, np.ndarray]:
    """Sample points and their normals from mesh surface."""
    points, face_indices = trimesh.sample.sample_surface(mesh, num_samples)
    normals = mesh.face_normals[face_indices]
    return points, normals


def chamfer_distance(
    predicted: trimesh.Trimesh,
    ground_truth: trimesh.Trimesh,
    num_samples: int = DEFAULT_NUM_SAMPLES,
) -> float:
    """
    Compute Chamfer Distance between two meshes.

    CD = (1/|P|) * sum(min_q ||p - q||^2) + (1/|Q|) * sum(min_p ||q - p||^2)

    :param predicted: Generated mesh
    :param ground_truth: Reference mesh
    :param num_samples: Number of surface points to sample
    :return: Chamfer distance (lower is better)
    """
    from scipy.spatial import cKDTree

    pts_pred, _ = _sample_points_and_normals(predicted, num_samples)
    pts_gt, _ = _sample_points_and_normals(ground_truth, num_samples)

    tree_pred = cKDTree(pts_pred)
    tree_gt = cKDTree(pts_gt)

    dist_pred_to_gt, _ = tree_gt.query(pts_pred)
    dist_gt_to_pred, _ = tree_pred.query(pts_gt)

    cd = float(np.mean(dist_pred_to_gt ** 2) + np.mean(dist_gt_to_pred ** 2))
    return cd


def iou_3d(
    predicted: trimesh.Trimesh,
    ground_truth: trimesh.Trimesh,
    resolution: int = DEFAULT_VOXEL_RESOLUTION,
) -> float:
    """
    Compute 3D Intersection over Union via voxelization.

    :param predicted: Generated mesh (should be watertight for best results)
    :param ground_truth: Reference mesh
    :param resolution: Voxel grid resolution per axis
    :return: IoU value in [0, 1] (higher is better)
    """
    # Compute shared bounding box
    all_vertices = np.vstack([predicted.vertices, ground_truth.vertices])
    bbox_min = all_vertices.min(axis=0) - 0.1
    bbox_max = all_vertices.max(axis=0) + 0.1

    # Create voxel grid
    grid_points = _create_grid(bbox_min, bbox_max, resolution)

    # Check containment
    pred_contains = _contains_points(predicted, grid_points)
    gt_contains = _contains_points(ground_truth, grid_points)

    intersection = np.logical_and(pred_contains, gt_contains).sum()
    union = np.logical_or(pred_contains, gt_contains).sum()

    if union == 0:
        return 0.0
    return float(intersection / union)


def f_score(
    predicted: trimesh.Trimesh,
    ground_truth: trimesh.Trimesh,
    threshold: float = DEFAULT_F_SCORE_THRESHOLD,
    num_samples: int = DEFAULT_NUM_SAMPLES,
) -> float:
    """
    Compute F-Score at a distance threshold.

    F-Score = 2 * (precision * recall) / (precision + recall)
    where precision = fraction of predicted points within threshold of GT
    and recall = fraction of GT points within threshold of predicted.

    :param predicted: Generated mesh
    :param ground_truth: Reference mesh
    :param threshold: Distance threshold (relative to bounding box diagonal)
    :param num_samples: Number of surface points to sample
    :return: F-Score in [0, 1] (higher is better)
    """
    from scipy.spatial import cKDTree

    pts_pred, _ = _sample_points_and_normals(predicted, num_samples)
    pts_gt, _ = _sample_points_and_normals(ground_truth, num_samples)

    # Scale threshold by bounding box diagonal
    all_pts = np.vstack([pts_pred, pts_gt])
    bbox_diag = np.linalg.norm(all_pts.max(axis=0) - all_pts.min(axis=0))
    abs_threshold = threshold * bbox_diag

    tree_pred = cKDTree(pts_pred)
    tree_gt = cKDTree(pts_gt)

    dist_pred_to_gt, _ = tree_gt.query(pts_pred)
    dist_gt_to_pred, _ = tree_pred.query(pts_gt)

    precision = float(np.mean(dist_pred_to_gt < abs_threshold))
    recall = float(np.mean(dist_gt_to_pred < abs_threshold))

    if precision + recall == 0:
        return 0.0
    return float(2 * precision * recall / (precision + recall))


def normal_consistency_comparison(
    predicted: trimesh.Trimesh,
    ground_truth: trimesh.Trimesh,
    num_samples: int = DEFAULT_NUM_SAMPLES,
) -> float:
    """
    Compute Normal Consistency between predicted and ground truth meshes.

    For each point on the predicted surface, find the nearest point on GT
    and compute the absolute dot product of their normals.

    :param predicted: Generated mesh
    :param ground_truth: Reference mesh
    :param num_samples: Number of surface points to sample
    :return: Normal consistency in [0, 1] (higher is better)
    """
    from scipy.spatial import cKDTree

    pts_pred, normals_pred = _sample_points_and_normals(predicted, num_samples)
    pts_gt, normals_gt = _sample_points_and_normals(ground_truth, num_samples)

    tree_gt = cKDTree(pts_gt)
    _, indices = tree_gt.query(pts_pred)

    matched_normals = normals_gt[indices]
    dots = np.abs(np.sum(normals_pred * matched_normals, axis=1))
    return float(np.mean(dots))


def compute_comparison_metrics(
    predicted: trimesh.Trimesh,
    ground_truth: trimesh.Trimesh,
    num_samples: int = DEFAULT_NUM_SAMPLES,
    voxel_resolution: int = DEFAULT_VOXEL_RESOLUTION,
    f_score_threshold: float = DEFAULT_F_SCORE_THRESHOLD,
) -> MeshQualityMetrics:
    """
    Compute all metrics including comparison with ground truth.

    :param predicted: Generated mesh
    :param ground_truth: Reference mesh
    :return: MeshQualityMetrics with all fields filled
    """
    metrics = compute_self_metrics(predicted)

    try:
        metrics.chamfer_distance = chamfer_distance(predicted, ground_truth, num_samples)
    except Exception as e:
        logger.warning("Failed to compute Chamfer Distance: %s", e)

    try:
        metrics.iou_3d = iou_3d(predicted, ground_truth, voxel_resolution)
    except Exception as e:
        logger.warning("Failed to compute IoU 3D: %s", e)

    try:
        metrics.f_score = f_score(
            predicted, ground_truth, f_score_threshold, num_samples
        )
    except Exception as e:
        logger.warning("Failed to compute F-Score: %s", e)

    try:
        metrics.normal_consistency = normal_consistency_comparison(
            predicted, ground_truth, num_samples
        )
    except Exception as e:
        logger.warning("Failed to compute Normal Consistency: %s", e)

    return metrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_grid(
    bbox_min: np.ndarray, bbox_max: np.ndarray, resolution: int
) -> np.ndarray:
    """Create a uniform 3D grid of points."""
    x = np.linspace(bbox_min[0], bbox_max[0], resolution)
    y = np.linspace(bbox_min[1], bbox_max[1], resolution)
    z = np.linspace(bbox_min[2], bbox_max[2], resolution)
    grid = np.stack(np.meshgrid(x, y, z, indexing="ij"), axis=-1)
    return grid.reshape(-1, 3)


def _contains_points(mesh: trimesh.Trimesh, points: np.ndarray) -> np.ndarray:
    """Check which points are inside a mesh using signed distance (no rtree needed)."""
    from scipy.spatial import cKDTree

    # Sample dense surface points and use proximity-based approach
    surface_pts, face_ids = trimesh.sample.sample_surface(mesh, max(10000, len(points)))
    surface_normals = mesh.face_normals[face_ids]

    tree = cKDTree(surface_pts)
    dists, indices = tree.query(points)

    # Use sign of dot product with surface normal to determine inside/outside
    to_point = points - surface_pts[indices]
    dots = np.sum(to_point * surface_normals[indices], axis=1)
    return dots < 0  # negative dot = inside
