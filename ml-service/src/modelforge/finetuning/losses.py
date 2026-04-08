"""Loss functions for TripoSR fine-tuning.

Implements Chamfer distance, mesh regularization losses,
and a combined loss for training.
"""

import logging
from dataclasses import dataclass
from typing import Dict

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LossResult:
    """Result of loss computation with individual components."""

    total: float
    components: Dict[str, float]


def chamfer_distance(
    pred_points: np.ndarray,
    target_points: np.ndarray,
) -> float:
    """Compute Chamfer distance between two point clouds.

    Chamfer distance = mean of nearest-neighbor distances in both directions.

    Args:
        pred_points: (N, 3) predicted point cloud
        target_points: (M, 3) ground truth point cloud

    Returns:
        Chamfer distance (lower is better).
    """
    if len(pred_points) == 0 or len(target_points) == 0:
        return float("inf")

    # pred -> target: for each pred point, find closest target point
    # Using broadcasting: (N, 1, 3) - (1, M, 3) -> (N, M, 3) -> (N, M)
    # Process in chunks to avoid memory issues with large point clouds
    chunk_size = 2048
    forward_mins = []

    for i in range(0, len(pred_points), chunk_size):
        chunk = pred_points[i : i + chunk_size]
        diff = chunk[:, np.newaxis, :] - target_points[np.newaxis, :, :]
        dists = np.sum(diff ** 2, axis=-1)  # (chunk, M)
        forward_mins.append(np.min(dists, axis=1))

    forward_dist = np.mean(np.concatenate(forward_mins))

    # target -> pred: for each target point, find closest pred point
    backward_mins = []

    for i in range(0, len(target_points), chunk_size):
        chunk = target_points[i : i + chunk_size]
        diff = chunk[:, np.newaxis, :] - pred_points[np.newaxis, :, :]
        dists = np.sum(diff ** 2, axis=-1)  # (chunk, N)
        backward_mins.append(np.min(dists, axis=1))

    backward_dist = np.mean(np.concatenate(backward_mins))

    return float(forward_dist + backward_dist)


def mesh_edge_loss(vertices: np.ndarray, faces: np.ndarray) -> float:
    """Penalize variance in edge lengths to encourage uniform meshes.

    Args:
        vertices: (V, 3) vertex positions
        faces: (F, 3) face indices

    Returns:
        Edge length variance (lower = more uniform mesh).
    """
    if len(faces) == 0 or len(vertices) == 0:
        return 0.0

    # Extract edges from faces
    edges = np.concatenate([
        faces[:, [0, 1]],
        faces[:, [1, 2]],
        faces[:, [2, 0]],
    ], axis=0)

    edge_vectors = vertices[edges[:, 1]] - vertices[edges[:, 0]]
    edge_lengths = np.linalg.norm(edge_vectors, axis=-1)

    if len(edge_lengths) == 0:
        return 0.0

    return float(np.var(edge_lengths))


def mesh_laplacian_loss(vertices: np.ndarray, faces: np.ndarray) -> float:
    """Laplacian smoothing loss to penalize irregular surfaces.

    Measures how far each vertex is from the centroid of its neighbors.

    Args:
        vertices: (V, 3) vertex positions
        faces: (F, 3) face indices

    Returns:
        Mean squared Laplacian (lower = smoother mesh).
    """
    if len(faces) == 0 or len(vertices) < 3:
        return 0.0

    n_verts = len(vertices)

    # Build adjacency: for each vertex, collect neighbors
    neighbors = [set() for _ in range(n_verts)]
    for f in faces:
        for i in range(3):
            for j in range(3):
                if i != j:
                    neighbors[f[i]].add(f[j])

    laplacian_sum = 0.0
    count = 0

    for i in range(n_verts):
        nbrs = neighbors[i]
        if not nbrs:
            continue
        centroid = np.mean(vertices[list(nbrs)], axis=0)
        laplacian_sum += np.sum((vertices[i] - centroid) ** 2)
        count += 1

    if count == 0:
        return 0.0

    return float(laplacian_sum / count)


def sample_surface_points(
    vertices: np.ndarray,
    faces: np.ndarray,
    n_points: int = 4096,
    seed: int = 42,
) -> np.ndarray:
    """Sample points uniformly on mesh surface for Chamfer distance.

    Args:
        vertices: (V, 3) vertex positions
        faces: (F, 3) face indices
        n_points: number of points to sample
        seed: random seed

    Returns:
        (n_points, 3) sampled points.
    """
    if len(faces) == 0 or len(vertices) == 0:
        return np.zeros((0, 3), dtype=np.float32)

    rng = np.random.RandomState(seed)

    # Compute face areas for weighted sampling
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]

    cross = np.cross(v1 - v0, v2 - v0)
    areas = 0.5 * np.linalg.norm(cross, axis=-1)
    total_area = areas.sum()

    if total_area < 1e-10:
        return np.zeros((0, 3), dtype=np.float32)

    probs = areas / total_area

    # Sample faces proportional to area
    face_indices = rng.choice(len(faces), size=n_points, p=probs)

    # Random barycentric coordinates
    r1 = rng.random(n_points).astype(np.float32)
    r2 = rng.random(n_points).astype(np.float32)
    sqrt_r1 = np.sqrt(r1)

    bary_u = 1 - sqrt_r1
    bary_v = sqrt_r1 * (1 - r2)
    bary_w = sqrt_r1 * r2

    sampled_v0 = vertices[faces[face_indices, 0]]
    sampled_v1 = vertices[faces[face_indices, 1]]
    sampled_v2 = vertices[faces[face_indices, 2]]

    points = (
        bary_u[:, np.newaxis] * sampled_v0
        + bary_v[:, np.newaxis] * sampled_v1
        + bary_w[:, np.newaxis] * sampled_v2
    )

    return points.astype(np.float32)


class CombinedLoss:
    """Combined loss function for TripoSR fine-tuning.

    Combines:
    - Chamfer distance (geometric accuracy)
    - Edge length regularization (mesh uniformity)
    - Laplacian smoothing (surface regularity)
    """

    def __init__(
        self,
        chamfer_weight: float = 1.0,
        edge_weight: float = 0.1,
        laplacian_weight: float = 0.05,
        n_surface_points: int = 4096,
    ):
        self.chamfer_weight = chamfer_weight
        self.edge_weight = edge_weight
        self.laplacian_weight = laplacian_weight
        self.n_surface_points = n_surface_points

    def compute(
        self,
        pred_vertices: np.ndarray,
        pred_faces: np.ndarray,
        target_vertices: np.ndarray,
        target_faces: np.ndarray,
    ) -> LossResult:
        """Compute combined loss between predicted and target meshes.

        Args:
            pred_vertices: predicted mesh vertices
            pred_faces: predicted mesh faces
            target_vertices: ground truth mesh vertices
            target_faces: ground truth mesh faces

        Returns:
            LossResult with total loss and individual components.
        """
        components = {}

        # Chamfer distance on sampled surface points
        pred_points = sample_surface_points(
            pred_vertices, pred_faces, self.n_surface_points
        )
        target_points = sample_surface_points(
            target_vertices, target_faces, self.n_surface_points
        )

        cd = chamfer_distance(pred_points, target_points)
        components["chamfer"] = cd

        # Edge regularization on predicted mesh
        edge = mesh_edge_loss(pred_vertices, pred_faces)
        components["edge"] = edge

        # Laplacian smoothing on predicted mesh
        lap = mesh_laplacian_loss(pred_vertices, pred_faces)
        components["laplacian"] = lap

        total = (
            self.chamfer_weight * cd
            + self.edge_weight * edge
            + self.laplacian_weight * lap
        )
        components["total"] = total

        return LossResult(total=total, components=components)
