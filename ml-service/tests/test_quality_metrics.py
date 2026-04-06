"""Tests for scientific 3D mesh quality metrics."""

import numpy as np
import pytest
import trimesh

from modelforge.metrics.quality import (
    MeshQualityMetrics,
    chamfer_distance,
    compute_comparison_metrics,
    compute_self_metrics,
    f_score,
    iou_3d,
    normal_consistency_comparison,
)


@pytest.fixture
def unit_cube():
    """A simple unit cube mesh."""
    return trimesh.creation.box(extents=[1, 1, 1])


@pytest.fixture
def unit_sphere():
    """A unit sphere mesh."""
    return trimesh.creation.icosphere(subdivisions=3, radius=0.5)


@pytest.fixture
def shifted_cube():
    """A cube shifted by 0.5 along X axis."""
    mesh = trimesh.creation.box(extents=[1, 1, 1])
    mesh.apply_translation([0.5, 0, 0])
    return mesh


class TestSelfMetrics:

    def test_vertex_and_face_count(self, unit_cube):
        metrics = compute_self_metrics(unit_cube)
        assert metrics.vertices == len(unit_cube.vertices)
        assert metrics.faces == len(unit_cube.faces)

    def test_watertight_cube(self, unit_cube):
        metrics = compute_self_metrics(unit_cube)
        assert metrics.is_watertight is True

    def test_normal_consistency_range(self, unit_cube):
        metrics = compute_self_metrics(unit_cube)
        assert metrics.normal_consistency is not None
        assert 0.0 <= metrics.normal_consistency <= 1.0

    def test_normal_consistency_high_for_cube(self, unit_cube):
        """Cube has perfectly aligned normals — consistency should be very high."""
        metrics = compute_self_metrics(unit_cube)
        assert metrics.normal_consistency > 0.9

    def test_comparison_metrics_are_none(self, unit_cube):
        """Self metrics should not include comparison metrics."""
        metrics = compute_self_metrics(unit_cube)
        assert metrics.chamfer_distance is None
        assert metrics.iou_3d is None
        assert metrics.f_score is None

    def test_to_dict_excludes_none(self, unit_cube):
        metrics = compute_self_metrics(unit_cube)
        d = metrics.to_dict()
        assert "chamfer_distance" not in d
        assert "vertices" in d
        assert "faces" in d


class TestChamferDistance:

    def test_identical_meshes(self, unit_cube):
        cd = chamfer_distance(unit_cube, unit_cube, num_samples=5000)
        assert cd < 0.01  # sampling introduces small noise

    def test_different_meshes_positive(self, unit_cube, unit_sphere):
        cd = chamfer_distance(unit_cube, unit_sphere, num_samples=5000)
        assert cd > 0

    def test_shifted_cube_nonzero(self, unit_cube, shifted_cube):
        cd = chamfer_distance(unit_cube, shifted_cube, num_samples=5000)
        assert cd > 0

    def test_symmetric(self, unit_cube, unit_sphere):
        cd1 = chamfer_distance(unit_cube, unit_sphere, num_samples=5000)
        cd2 = chamfer_distance(unit_sphere, unit_cube, num_samples=5000)
        assert abs(cd1 - cd2) < 0.05  # approximately symmetric


class TestIoU3D:

    def test_identical_meshes(self, unit_cube):
        iou = iou_3d(unit_cube, unit_cube, resolution=16)
        assert iou > 0.95

    def test_no_overlap(self):
        cube1 = trimesh.creation.box(extents=[1, 1, 1])
        cube2 = trimesh.creation.box(extents=[1, 1, 1])
        cube2.apply_translation([5, 0, 0])  # far apart
        iou = iou_3d(cube1, cube2, resolution=16)
        assert iou < 0.05

    def test_partial_overlap(self, unit_cube, shifted_cube):
        iou = iou_3d(unit_cube, shifted_cube, resolution=16)
        assert 0.1 < iou < 0.9


class TestFScore:

    def test_identical_meshes(self, unit_cube):
        fs = f_score(unit_cube, unit_cube, threshold=0.05, num_samples=5000)
        assert fs > 0.8

    def test_different_meshes_lower(self, unit_cube, unit_sphere):
        fs = f_score(unit_cube, unit_sphere, num_samples=5000)
        assert 0.0 <= fs <= 1.0

    def test_range(self, unit_cube, shifted_cube):
        fs = f_score(unit_cube, shifted_cube, num_samples=5000)
        assert 0.0 <= fs <= 1.0


class TestNormalConsistencyComparison:

    def test_identical_meshes(self, unit_cube):
        nc = normal_consistency_comparison(unit_cube, unit_cube, num_samples=5000)
        assert nc > 0.95

    def test_range(self, unit_cube, unit_sphere):
        nc = normal_consistency_comparison(unit_cube, unit_sphere, num_samples=5000)
        assert 0.0 <= nc <= 1.0


class TestComparisonMetrics:

    def test_all_fields_populated(self, unit_cube, unit_sphere):
        metrics = compute_comparison_metrics(unit_cube, unit_sphere, num_samples=5000, voxel_resolution=16)
        assert metrics.vertices > 0
        assert metrics.faces > 0
        assert metrics.chamfer_distance is not None
        assert metrics.iou_3d is not None
        assert metrics.f_score is not None
        assert metrics.normal_consistency is not None

    def test_identical_meshes_good_scores(self, unit_cube):
        metrics = compute_comparison_metrics(
            unit_cube, unit_cube, num_samples=5000, voxel_resolution=16
        )
        assert metrics.chamfer_distance < 0.01
        assert metrics.iou_3d is not None and metrics.iou_3d > 0.5
        assert metrics.f_score is not None
        assert metrics.normal_consistency > 0.9
