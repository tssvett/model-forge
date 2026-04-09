"""Tests for fine-tuned weight management."""

import json
import time
from pathlib import Path

import pytest

from modelforge.finetuning.weight_manager import (
    MODEL_VERSION_BASE,
    REGISTRY_FILENAME,
    ModelRegistry,
    ModelVersion,
    WeightManager,
)


@pytest.fixture
def checkpoint_dir(tmp_path):
    """Create a temporary checkpoint directory."""
    d = tmp_path / "checkpoints"
    d.mkdir()
    return d


@pytest.fixture
def manager(checkpoint_dir):
    """Create a WeightManager with a temp directory."""
    return WeightManager(checkpoint_dir=checkpoint_dir)


class TestModelVersion:
    def test_to_dict_roundtrip(self):
        version = ModelVersion(
            version_id="finetuned-v1",
            description="Test version",
            checkpoint_path="/path/to/checkpoint",
            is_finetuned=True,
            val_loss=0.05,
            training_epochs=10,
            dataset_type="shapenet",
            metrics={"accuracy": 0.95},
        )
        data = version.to_dict()
        restored = ModelVersion.from_dict(data)

        assert restored.version_id == "finetuned-v1"
        assert restored.description == "Test version"
        assert restored.checkpoint_path == "/path/to/checkpoint"
        assert restored.is_finetuned is True
        assert restored.val_loss == 0.05
        assert restored.training_epochs == 10
        assert restored.dataset_type == "shapenet"
        assert restored.metrics == {"accuracy": 0.95}

    def test_from_dict_ignores_extra_fields(self):
        data = {
            "version_id": "v1",
            "description": "test",
            "checkpoint_path": "/tmp",
            "unknown_field": "ignored",
        }
        version = ModelVersion.from_dict(data)
        assert version.version_id == "v1"


class TestModelRegistry:
    def test_to_dict_roundtrip(self):
        registry = ModelRegistry()
        registry.versions["v1"] = ModelVersion(
            version_id="v1",
            description="Test",
            checkpoint_path="/tmp/v1",
        )
        registry.active_version = "v1"

        data = registry.to_dict()
        restored = ModelRegistry.from_dict(data)

        assert restored.active_version == "v1"
        assert "v1" in restored.versions
        assert restored.versions["v1"].description == "Test"

    def test_empty_registry(self):
        registry = ModelRegistry.from_dict({})
        assert registry.active_version == MODEL_VERSION_BASE
        assert len(registry.versions) == 0


class TestWeightManager:
    def test_register_checkpoint(self, manager):
        version = manager.register_checkpoint(
            version_id="finetuned-v1",
            checkpoint_path="/path/to/ckpt",
            description="First fine-tuned version",
            val_loss=0.042,
            training_epochs=25,
            dataset_type="shapenet",
        )

        assert version.version_id == "finetuned-v1"
        assert version.is_finetuned is True
        assert version.val_loss == 0.042

        # Registry should be persisted
        assert manager.get_version("finetuned-v1") is not None

    def test_list_versions_sorted_by_time(self, manager):
        manager.register_checkpoint("v1", "/p1", description="First")
        time.sleep(0.01)
        manager.register_checkpoint("v2", "/p2", description="Second")

        versions = manager.list_versions()
        assert len(versions) == 2
        assert versions[0].version_id == "v2"  # most recent first
        assert versions[1].version_id == "v1"

    def test_set_active_version(self, manager):
        manager.register_checkpoint("v1", "/p1")
        manager.set_active_version("v1")
        assert manager.get_active_version() == "v1"

    def test_set_active_version_base(self, manager):
        manager.set_active_version(MODEL_VERSION_BASE)
        assert manager.get_active_version() == MODEL_VERSION_BASE

    def test_set_active_version_unknown_raises(self, manager):
        with pytest.raises(ValueError, match="Unknown version"):
            manager.set_active_version("nonexistent")

    def test_remove_version(self, manager):
        manager.register_checkpoint("v1", "/p1")
        assert manager.remove_version("v1") is True
        assert manager.get_version("v1") is None

    def test_remove_version_resets_active(self, manager):
        manager.register_checkpoint("v1", "/p1")
        manager.set_active_version("v1")
        manager.remove_version("v1")
        assert manager.get_active_version() == MODEL_VERSION_BASE

    def test_remove_base_returns_false(self, manager):
        assert manager.remove_version(MODEL_VERSION_BASE) is False

    def test_remove_nonexistent_returns_false(self, manager):
        assert manager.remove_version("ghost") is False

    def test_get_checkpoint_path_base_returns_none(self, manager):
        assert manager.get_checkpoint_path(MODEL_VERSION_BASE) is None

    def test_get_checkpoint_path_finetuned(self, manager):
        manager.register_checkpoint("v1", "/path/to/weights")
        assert manager.get_checkpoint_path("v1") == "/path/to/weights"

    def test_get_checkpoint_path_active(self, manager):
        manager.register_checkpoint("v1", "/path/to/weights")
        manager.set_active_version("v1")
        assert manager.get_checkpoint_path() == "/path/to/weights"

    def test_registry_persistence(self, checkpoint_dir):
        # Register a version in one manager instance
        manager1 = WeightManager(checkpoint_dir=checkpoint_dir)
        manager1.register_checkpoint("v1", "/p1", description="Persistent")
        manager1.set_active_version("v1")

        # Load a fresh manager — should see the same data
        manager2 = WeightManager(checkpoint_dir=checkpoint_dir)
        assert manager2.get_active_version() == "v1"
        assert manager2.get_version("v1").description == "Persistent"

    def test_discover_checkpoints(self, checkpoint_dir):
        # Create an unregistered checkpoint
        sub = checkpoint_dir / "training_run_1"
        sub.mkdir()
        best = sub / "checkpoint_best.json"
        best.write_text(json.dumps({"epoch": 5, "best_val_loss": 0.03}))

        manager = WeightManager(checkpoint_dir=checkpoint_dir)
        discovered = manager.discover_checkpoints()
        assert len(discovered) == 1
        assert str(sub) in discovered[0]

    def test_discover_skips_registered(self, checkpoint_dir):
        sub = checkpoint_dir / "run1"
        sub.mkdir()
        (sub / "checkpoint_best.json").write_text("{}")

        manager = WeightManager(checkpoint_dir=checkpoint_dir)
        manager.register_checkpoint("v1", str(sub))

        discovered = manager.discover_checkpoints()
        assert len(discovered) == 0

    def test_auto_register_from_training(self, checkpoint_dir):
        training_dir = checkpoint_dir / "training_run"
        training_dir.mkdir()
        (training_dir / "checkpoint_best.json").write_text(
            json.dumps({
                "epoch": 15,
                "best_val_loss": 0.028,
                "training_config": {"learning_rate": 0.0001},
                "train_losses": [0.5, 0.3, 0.1],
                "val_losses": [0.4, 0.2, 0.028],
            })
        )

        manager = WeightManager(checkpoint_dir=checkpoint_dir)
        version_id = manager.auto_register_from_training(training_dir)

        assert version_id is not None
        assert version_id.startswith("finetuned-e15-")
        version = manager.get_version(version_id)
        assert version.val_loss == 0.028
        assert version.training_epochs == 16
        assert version.is_finetuned is True

    def test_auto_register_missing_checkpoint(self, checkpoint_dir):
        manager = WeightManager(checkpoint_dir=checkpoint_dir)
        result = manager.auto_register_from_training(checkpoint_dir / "nonexistent")
        assert result is None

    def test_upload_no_s3_returns_false(self, manager):
        manager.register_checkpoint("v1", "/p1")
        assert manager.upload_checkpoint("v1") is False

    def test_download_no_s3_returns_false(self, manager):
        assert manager.download_checkpoint("v1") is False
