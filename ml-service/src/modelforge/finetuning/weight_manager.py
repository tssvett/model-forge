"""Fine-tuned weight management for TripoSR.

Manages model checkpoints: registration, discovery, loading metadata,
and synchronization with S3 (MinIO) for distributed access.

Supports switching between base and fine-tuned models at runtime.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MODEL_VERSION_BASE = "base"
REGISTRY_FILENAME = "model_registry.json"
WEIGHTS_FILENAME = "model_weights.pt"
METADATA_FILENAME = "metadata.json"


@dataclass
class ModelVersion:
    """Metadata for a registered model version."""

    version_id: str
    description: str
    checkpoint_path: str
    is_finetuned: bool = False
    base_model: str = "stabilityai/TripoSR"
    created_at: float = field(default_factory=time.time)
    val_loss: Optional[float] = None
    training_epochs: Optional[int] = None
    dataset_type: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelVersion":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ModelRegistry:
    """Registry of available model versions."""

    active_version: str = MODEL_VERSION_BASE
    versions: Dict[str, ModelVersion] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_version": self.active_version,
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelRegistry":
        versions = {
            k: ModelVersion.from_dict(v)
            for k, v in data.get("versions", {}).items()
        }
        return cls(
            active_version=data.get("active_version", MODEL_VERSION_BASE),
            versions=versions,
        )


class WeightManager:
    """Manages fine-tuned model weights and version switching.

    Responsibilities:
    - Discover and register checkpoint files from training runs
    - Track model versions with metadata (loss, epochs, dataset)
    - Switch active model version at runtime
    - Upload/download checkpoints to/from S3 (MinIO)
    """

    def __init__(
        self,
        checkpoint_dir: Path,
        s3_storage=None,
        s3_prefix: str = "checkpoints/triposr",
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.s3_storage = s3_storage
        self.s3_prefix = s3_prefix
        self.registry = self._load_registry()

    def _registry_path(self) -> Path:
        return self.checkpoint_dir / REGISTRY_FILENAME

    def _load_registry(self) -> ModelRegistry:
        """Load the model registry from disk."""
        path = self._registry_path()
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                registry = ModelRegistry.from_dict(data)
                logger.info(
                    "Loaded model registry: %d versions, active=%s",
                    len(registry.versions),
                    registry.active_version,
                )
                return registry
            except Exception as e:
                logger.warning("Failed to load registry: %s, creating new", e)
        return ModelRegistry()

    def _save_registry(self) -> None:
        """Persist the registry to disk."""
        path = self._registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.registry.to_dict(), f, indent=2)
        logger.debug("Registry saved to %s", path)

    def register_checkpoint(
        self,
        version_id: str,
        checkpoint_path: str,
        description: str = "",
        val_loss: Optional[float] = None,
        training_epochs: Optional[int] = None,
        dataset_type: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ModelVersion:
        """Register a fine-tuned checkpoint as a model version.

        Args:
            version_id: Unique version identifier (e.g., "finetuned-v1")
            checkpoint_path: Path to the checkpoint directory or weights file
            description: Human-readable description
            val_loss: Best validation loss achieved
            training_epochs: Number of epochs trained
            dataset_type: Dataset used for training
            metrics: Additional metrics dict

        Returns:
            The registered ModelVersion
        """
        version = ModelVersion(
            version_id=version_id,
            description=description,
            checkpoint_path=str(checkpoint_path),
            is_finetuned=True,
            val_loss=val_loss,
            training_epochs=training_epochs,
            dataset_type=dataset_type,
            metrics=metrics or {},
        )
        self.registry.versions[version_id] = version
        self._save_registry()
        logger.info("Registered model version: %s (%s)", version_id, description)
        return version

    def get_version(self, version_id: str) -> Optional[ModelVersion]:
        """Get metadata for a specific model version."""
        return self.registry.versions.get(version_id)

    def list_versions(self) -> List[ModelVersion]:
        """List all registered model versions, sorted by creation time."""
        return sorted(
            self.registry.versions.values(),
            key=lambda v: v.created_at,
            reverse=True,
        )

    def get_active_version(self) -> str:
        """Get the currently active model version ID."""
        return self.registry.active_version

    def set_active_version(self, version_id: str) -> None:
        """Switch the active model version.

        Args:
            version_id: Version to activate ("base" or a registered version)

        Raises:
            ValueError: If version_id is not registered
        """
        if version_id != MODEL_VERSION_BASE and version_id not in self.registry.versions:
            available = [MODEL_VERSION_BASE] + list(self.registry.versions.keys())
            raise ValueError(
                f"Unknown version '{version_id}'. Available: {available}"
            )
        self.registry.active_version = version_id
        self._save_registry()
        logger.info("Active model version set to: %s", version_id)

    def remove_version(self, version_id: str) -> bool:
        """Remove a model version from the registry.

        Does not delete checkpoint files — only removes the registry entry.
        """
        if version_id == MODEL_VERSION_BASE:
            logger.warning("Cannot remove base model version")
            return False
        if version_id not in self.registry.versions:
            return False

        del self.registry.versions[version_id]

        if self.registry.active_version == version_id:
            self.registry.active_version = MODEL_VERSION_BASE
            logger.info("Active version reset to base (removed version was active)")

        self._save_registry()
        logger.info("Removed model version: %s", version_id)
        return True

    def get_checkpoint_path(self, version_id: Optional[str] = None) -> Optional[str]:
        """Get the checkpoint path for a version (or active version if None).

        Returns None for the base model (uses HuggingFace pretrained).
        """
        version_id = version_id or self.registry.active_version
        if version_id == MODEL_VERSION_BASE:
            return None

        version = self.registry.versions.get(version_id)
        if version is None:
            logger.warning("Version '%s' not found in registry", version_id)
            return None
        return version.checkpoint_path

    def discover_checkpoints(self) -> List[str]:
        """Scan checkpoint_dir for unregistered checkpoint files.

        Looks for checkpoint_best.json files from training runs
        and model_weights.pt files.
        """
        discovered = []
        registered_paths = {v.checkpoint_path for v in self.registry.versions.values()}

        for path in self.checkpoint_dir.rglob("checkpoint_best.json"):
            str_path = str(path.parent)
            if str_path not in registered_paths:
                discovered.append(str_path)
                logger.info("Discovered unregistered checkpoint: %s", str_path)

        for path in self.checkpoint_dir.rglob(WEIGHTS_FILENAME):
            str_path = str(path.parent)
            if str_path not in registered_paths:
                discovered.append(str_path)

        return discovered

    def upload_checkpoint(self, version_id: str) -> bool:
        """Upload a checkpoint to S3 (MinIO) for distributed access.

        Uploads both the weights file and metadata.
        """
        if self.s3_storage is None:
            logger.warning("S3 storage not configured, cannot upload")
            return False

        version = self.registry.versions.get(version_id)
        if version is None:
            logger.error("Version '%s' not found", version_id)
            return False

        checkpoint_path = Path(version.checkpoint_path)

        try:
            # Upload metadata
            metadata_key = f"{self.s3_prefix}/{version_id}/{METADATA_FILENAME}"
            metadata_bytes = json.dumps(version.to_dict(), indent=2).encode()
            self.s3_storage.upload_bytes(metadata_bytes, metadata_key)
            logger.info("Uploaded metadata: %s", metadata_key)

            # Upload weights file if it exists
            weights_path = checkpoint_path / WEIGHTS_FILENAME
            if weights_path.exists():
                weights_key = f"{self.s3_prefix}/{version_id}/{WEIGHTS_FILENAME}"
                with open(weights_path, "rb") as f:
                    self.s3_storage.upload_bytes(f.read(), weights_key)
                logger.info("Uploaded weights: %s", weights_key)

            # Upload training checkpoint JSON if it exists
            best_checkpoint = checkpoint_path / "checkpoint_best.json"
            if best_checkpoint.exists():
                ckpt_key = f"{self.s3_prefix}/{version_id}/checkpoint_best.json"
                with open(best_checkpoint, "rb") as f:
                    self.s3_storage.upload_bytes(f.read(), ckpt_key)
                logger.info("Uploaded checkpoint: %s", ckpt_key)

            return True

        except Exception as e:
            logger.error("Failed to upload checkpoint %s: %s", version_id, e)
            return False

    def download_checkpoint(self, version_id: str) -> bool:
        """Download a checkpoint from S3 (MinIO) to local storage."""
        if self.s3_storage is None:
            logger.warning("S3 storage not configured, cannot download")
            return False

        try:
            local_dir = self.checkpoint_dir / version_id
            local_dir.mkdir(parents=True, exist_ok=True)

            # Download metadata
            metadata_key = f"{self.s3_prefix}/{version_id}/{METADATA_FILENAME}"
            metadata_bytes = self.s3_storage.download_bytes(metadata_key)
            if metadata_bytes:
                metadata_path = local_dir / METADATA_FILENAME
                with open(metadata_path, "wb") as f:
                    f.write(metadata_bytes)

                # Register from downloaded metadata
                metadata = json.loads(metadata_bytes)
                metadata["checkpoint_path"] = str(local_dir)
                version = ModelVersion.from_dict(metadata)
                self.registry.versions[version_id] = version
                self._save_registry()

            # Download weights
            weights_key = f"{self.s3_prefix}/{version_id}/{WEIGHTS_FILENAME}"
            weights_bytes = self.s3_storage.download_bytes(weights_key)
            if weights_bytes:
                weights_path = local_dir / WEIGHTS_FILENAME
                with open(weights_path, "wb") as f:
                    f.write(weights_bytes)
                logger.info("Downloaded weights to %s", weights_path)

            # Download training checkpoint
            ckpt_key = f"{self.s3_prefix}/{version_id}/checkpoint_best.json"
            ckpt_bytes = self.s3_storage.download_bytes(ckpt_key)
            if ckpt_bytes:
                ckpt_path = local_dir / "checkpoint_best.json"
                with open(ckpt_path, "wb") as f:
                    f.write(ckpt_bytes)

            logger.info("Downloaded checkpoint for version '%s'", version_id)
            return True

        except Exception as e:
            logger.error("Failed to download checkpoint %s: %s", version_id, e)
            return False

    def auto_register_from_training(self, training_checkpoint_dir: Path) -> Optional[str]:
        """Auto-register a checkpoint produced by TripoSRTrainer.

        Reads the checkpoint_best.json from a training run,
        extracts metadata, and registers it as a new version.

        Returns the version_id if registered, None otherwise.
        """
        best_path = training_checkpoint_dir / "checkpoint_best.json"
        if not best_path.exists():
            logger.warning("No best checkpoint found at %s", best_path)
            return None

        try:
            with open(best_path, "r") as f:
                data = json.load(f)

            epoch = data.get("epoch", 0)
            val_loss = data.get("best_val_loss", None)
            config = data.get("training_config", {})

            version_id = f"finetuned-e{epoch}-{int(time.time())}"
            self.register_checkpoint(
                version_id=version_id,
                checkpoint_path=str(training_checkpoint_dir),
                description=f"Auto-registered from training (epoch {epoch})",
                val_loss=val_loss,
                training_epochs=epoch + 1,
                metrics={
                    "training_config": config,
                    "train_losses": data.get("train_losses", []),
                    "val_losses": data.get("val_losses", []),
                },
            )
            return version_id

        except Exception as e:
            logger.error("Failed to auto-register checkpoint: %s", e)
            return None
