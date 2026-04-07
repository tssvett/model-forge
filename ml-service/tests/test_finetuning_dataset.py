"""Tests for fine-tuning dataset preparation module."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from modelforge.finetuning.config import FinetuningConfig
from modelforge.finetuning.dataset import (
    DatasetSplit,
    DataSample,
    ImageAugmentor,
    MeshData,
    ShapeNetDataset,
    create_data_loaders,
)


@pytest.fixture
def temp_dataset(tmp_path):
    """Create a temporary ShapeNet-style dataset."""
    categories = ["chair", "table"]
    models_per_category = 5
    images_per_model = 2

    for cat in categories:
        cat_dir = tmp_path / cat
        for i in range(models_per_category):
            model_dir = cat_dir / f"model_{i:03d}"
            images_dir = model_dir / "images"
            images_dir.mkdir(parents=True)

            # Create dummy images
            for j in range(images_per_model):
                img = Image.new("RGB", (256, 256), color=(100 + j * 10, 150, 200))
                img.save(images_dir / f"{j:03d}.png")

            # Create OBJ mesh
            with open(model_dir / "model.obj", "w") as f:
                f.write("# Test mesh\n")
                f.write("v 0.0 0.0 0.0\n")
                f.write("v 1.0 0.0 0.0\n")
                f.write("v 0.0 1.0 0.0\n")
                f.write("v 0.0 0.0 1.0\n")
                f.write("f 1 2 3\n")
                f.write("f 1 2 4\n")
                f.write("f 1 3 4\n")
                f.write("f 2 3 4\n")

            # Create metadata
            with open(model_dir / "metadata.json", "w") as f:
                json.dump({"category": cat, "source": "test"}, f)

    return tmp_path


@pytest.fixture
def config(temp_dataset):
    return FinetuningConfig(
        dataset_root=temp_dataset,
        train_ratio=0.6,
        val_ratio=0.2,
        test_ratio=0.2,
        image_size=128,
        seed=42,
    )


# === Config Tests ===


class TestFinetuningConfig:
    def test_default_config(self):
        cfg = FinetuningConfig()
        assert cfg.train_ratio + cfg.val_ratio + cfg.test_ratio == 1.0
        assert cfg.batch_size == 4
        assert cfg.image_size == 512

    def test_invalid_split_ratios(self):
        with pytest.raises(ValueError, match="Split ratios must sum to 1.0"):
            FinetuningConfig(train_ratio=0.5, val_ratio=0.5, test_ratio=0.5)

    def test_invalid_batch_size(self):
        with pytest.raises(ValueError, match="batch_size must be >= 1"):
            FinetuningConfig(batch_size=0)

    def test_path_conversion(self):
        cfg = FinetuningConfig(dataset_root="some/path")
        assert isinstance(cfg.dataset_root, Path)

    def test_category_filter(self):
        cfg = FinetuningConfig(categories=["chair", "table"])
        assert cfg.categories == ["chair", "table"]


# === MeshData Tests ===


class TestMeshData:
    def test_valid_mesh(self):
        mesh = MeshData(
            vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2]], dtype=np.int64),
            vertex_count=3,
            face_count=1,
        )
        assert mesh.is_valid

    def test_empty_mesh_invalid(self):
        mesh = MeshData(
            vertices=np.zeros((0, 3), dtype=np.float32),
            faces=np.zeros((0, 3), dtype=np.int64),
            vertex_count=0,
            face_count=0,
        )
        assert not mesh.is_valid


# === Augmentor Tests ===


class TestImageAugmentor:
    def test_augmentation_disabled(self):
        cfg = FinetuningConfig(augmentation_enabled=False)
        aug = ImageAugmentor(cfg)
        img = Image.new("RGB", (128, 128), color=(100, 150, 200))
        result = aug.augment(img)
        assert result.size == img.size
        assert np.array_equal(np.array(result), np.array(img))

    def test_augmentation_returns_same_size(self):
        cfg = FinetuningConfig(augmentation_enabled=True)
        aug = ImageAugmentor(cfg)
        img = Image.new("RGB", (128, 128), color=(100, 150, 200))
        result = aug.augment(img)
        assert result.size == (128, 128)

    def test_color_jitter_preserves_shape(self):
        cfg = FinetuningConfig(
            augmentation_enabled=True,
            augmentation_horizontal_flip=False,
            augmentation_rotation_degrees=0,
            augmentation_color_jitter=True,
        )
        aug = ImageAugmentor(cfg)
        img = Image.new("RGB", (64, 64), color=(128, 128, 128))
        result = aug.augment(img)
        assert result.size == (64, 64)


# === Dataset Tests ===


class TestShapeNetDataset:
    def test_scan_finds_samples(self, config):
        ds = ShapeNetDataset(config=config, split=DatasetSplit.TRAIN)
        assert len(ds) > 0

    def test_split_sizes_add_up(self, config):
        train = ShapeNetDataset(config=config, split=DatasetSplit.TRAIN)
        val = ShapeNetDataset(config=config, split=DatasetSplit.VAL)
        test = ShapeNetDataset(config=config, split=DatasetSplit.TEST)

        total = len(train) + len(val) + len(test)
        # 2 categories * 5 models * 2 images = 20 total samples
        assert total == 20

    def test_splits_are_disjoint(self, config):
        train = ShapeNetDataset(config=config, split=DatasetSplit.TRAIN)
        val = ShapeNetDataset(config=config, split=DatasetSplit.VAL)
        test = ShapeNetDataset(config=config, split=DatasetSplit.TEST)

        train_ids = {(s.category, s.model_id, s.image_path.name) for s in train.samples}
        val_ids = {(s.category, s.model_id, s.image_path.name) for s in val.samples}
        test_ids = {(s.category, s.model_id, s.image_path.name) for s in test.samples}

        assert train_ids.isdisjoint(val_ids)
        assert train_ids.isdisjoint(test_ids)
        assert val_ids.isdisjoint(test_ids)

    def test_deterministic_splits(self, config):
        ds1 = ShapeNetDataset(config=config, split=DatasetSplit.TRAIN)
        ds2 = ShapeNetDataset(config=config, split=DatasetSplit.TRAIN)

        paths1 = [str(s.image_path) for s in ds1.samples]
        paths2 = [str(s.image_path) for s in ds2.samples]
        assert paths1 == paths2

    def test_getitem_returns_tuple(self, config):
        ds = ShapeNetDataset(config=config, split=DatasetSplit.TRAIN)
        if len(ds) > 0:
            image, mesh, sample = ds[0]
            assert isinstance(image, Image.Image)
            assert isinstance(mesh, MeshData)
            assert isinstance(sample, DataSample)
            assert image.size == (config.image_size, config.image_size)

    def test_obj_mesh_loading(self, config):
        ds = ShapeNetDataset(config=config, split=DatasetSplit.TRAIN)
        if len(ds) > 0:
            _, mesh, _ = ds[0]
            assert mesh.vertex_count == 4
            assert mesh.face_count == 4
            assert mesh.is_valid

    def test_category_filter(self, temp_dataset):
        cfg = FinetuningConfig(
            dataset_root=temp_dataset,
            categories=["chair"],
            seed=42,
        )
        ds = ShapeNetDataset(config=cfg, split=DatasetSplit.TRAIN)
        for sample in ds.samples:
            assert sample.category == "chair"

    def test_metadata_loaded(self, config):
        ds = ShapeNetDataset(config=config, split=DatasetSplit.TRAIN)
        if len(ds) > 0:
            sample = ds.samples[0]
            assert "category" in sample.metadata
            assert "source" in sample.metadata

    def test_empty_dataset(self, tmp_path):
        cfg = FinetuningConfig(dataset_root=tmp_path / "nonexistent")
        ds = ShapeNetDataset(config=cfg, split=DatasetSplit.TRAIN)
        assert len(ds) == 0

    def test_statistics(self, config):
        ds = ShapeNetDataset(config=config, split=DatasetSplit.TRAIN)
        stats = ds.get_statistics()
        assert stats["split"] == "train"
        assert stats["total_samples"] == len(ds)
        assert "categories" in stats


# === PLY Loading Test ===


class TestPlyLoading:
    def test_load_ply_mesh(self, tmp_path):
        # Create a simple PLY file
        ply_content = """ply
format ascii 1.0
element vertex 4
property float x
property float y
property float z
element face 2
property list uchar int vertex_indices
end_header
0.0 0.0 0.0
1.0 0.0 0.0
0.0 1.0 0.0
0.0 0.0 1.0
3 0 1 2
3 0 1 3
"""
        # Set up dataset structure
        cat_dir = tmp_path / "test_cat" / "model_000"
        images_dir = cat_dir / "images"
        images_dir.mkdir(parents=True)
        Image.new("RGB", (64, 64)).save(images_dir / "000.png")

        with open(cat_dir / "model.ply", "w") as f:
            f.write(ply_content)

        cfg = FinetuningConfig(dataset_root=tmp_path, image_size=64)
        ds = ShapeNetDataset(config=cfg, split=DatasetSplit.TRAIN)

        if len(ds) > 0:
            _, mesh, _ = ds[0]
            assert mesh.vertex_count == 4
            assert mesh.face_count == 2


# === create_data_loaders Tests ===


class TestCreateDataLoaders:
    def test_creates_all_splits(self, config):
        loaders = create_data_loaders(config)
        assert DatasetSplit.TRAIN in loaders
        assert DatasetSplit.VAL in loaders
        assert DatasetSplit.TEST in loaders

    def test_train_has_most_samples(self, config):
        loaders = create_data_loaders(config)
        assert len(loaders[DatasetSplit.TRAIN]) >= len(loaders[DatasetSplit.VAL])
        assert len(loaders[DatasetSplit.TRAIN]) >= len(loaders[DatasetSplit.TEST])
