"""Dataset loading and preparation for TripoSR fine-tuning.

Supports ShapeNet and Objaverse datasets with image-mesh pair loading,
train/val/test splitting, and data augmentation.
"""

import json
import logging
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from PIL import Image

from .config import FinetuningConfig

logger = logging.getLogger(__name__)


class DatasetSplit(str, Enum):
    TRAIN = "train"
    VAL = "val"
    TEST = "test"


@dataclass
class DataSample:
    """A single image-mesh pair for fine-tuning."""

    image_path: Path
    mesh_path: Path
    category: str
    model_id: str
    metadata: Dict[str, Any]


@dataclass
class MeshData:
    """Loaded mesh data with vertices and faces."""

    vertices: np.ndarray  # (N, 3) float32
    faces: np.ndarray  # (M, 3) int64
    vertex_count: int
    face_count: int

    @property
    def is_valid(self) -> bool:
        return self.vertex_count >= 3 and self.face_count >= 1


class ImageAugmentor:
    """Applies data augmentation to training images."""

    def __init__(self, config: FinetuningConfig):
        self.config = config

    def augment(self, image: Image.Image) -> Image.Image:
        if not self.config.augmentation_enabled:
            return image

        if self.config.augmentation_horizontal_flip and random.random() > 0.5:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)

        if self.config.augmentation_rotation_degrees > 0:
            angle = random.uniform(
                -self.config.augmentation_rotation_degrees,
                self.config.augmentation_rotation_degrees,
            )
            image = image.rotate(angle, resample=Image.BILINEAR, fillcolor=(255, 255, 255))

        if self.config.augmentation_color_jitter:
            image = self._apply_color_jitter(image)

        return image

    def _apply_color_jitter(self, image: Image.Image) -> Image.Image:
        """Apply random brightness and contrast adjustments."""
        img_array = np.array(image, dtype=np.float32)

        # Brightness
        brightness_factor = 1.0 + random.uniform(
            -self.config.augmentation_brightness,
            self.config.augmentation_brightness,
        )
        img_array = img_array * brightness_factor

        # Contrast
        contrast_factor = 1.0 + random.uniform(
            -self.config.augmentation_contrast,
            self.config.augmentation_contrast,
        )
        mean = img_array.mean()
        img_array = (img_array - mean) * contrast_factor + mean

        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        return Image.fromarray(img_array)


class ShapeNetDataset:
    """Dataset loader for ShapeNet-style directory structure.

    Expected structure:
        dataset_root/
            <category_id>/
                <model_id>/
                    images/
                        000.png (rendered views)
                        001.png
                        ...
                    model.obj (or model.glb)
                    metadata.json (optional)

    Also supports Objaverse-style flat structure:
        dataset_root/
            <model_id>/
                image.png
                mesh.glb
    """

    def __init__(self, config: FinetuningConfig, split: DatasetSplit):
        self.config = config
        self.split = split
        self.augmentor = ImageAugmentor(config) if split == DatasetSplit.TRAIN else None
        self.samples: List[DataSample] = []
        self._scan_and_split()

    def _scan_and_split(self):
        """Scan dataset directory and assign samples to the correct split."""
        root = self.config.dataset_root
        if not root.exists():
            logger.warning("Dataset root does not exist: %s", root)
            return

        all_samples = self._scan_directory(root)
        if not all_samples:
            logger.warning("No valid samples found in %s", root)
            return

        # Deterministic shuffle for reproducible splits
        rng = random.Random(self.config.seed)
        rng.shuffle(all_samples)

        n = len(all_samples)
        train_end = int(n * self.config.train_ratio)
        val_end = train_end + int(n * self.config.val_ratio)

        splits = {
            DatasetSplit.TRAIN: all_samples[:train_end],
            DatasetSplit.VAL: all_samples[train_end:val_end],
            DatasetSplit.TEST: all_samples[val_end:],
        }

        self.samples = splits[self.split]
        logger.info(
            "Dataset split=%s: %d samples (total=%d, train=%d, val=%d, test=%d)",
            self.split.value,
            len(self.samples),
            n,
            len(splits[DatasetSplit.TRAIN]),
            len(splits[DatasetSplit.VAL]),
            len(splits[DatasetSplit.TEST]),
        )

    def _scan_directory(self, root: Path) -> List[DataSample]:
        """Scan for valid image-mesh pairs."""
        samples = []
        mesh_extensions = {".obj", ".glb", ".stl", ".ply"}
        image_extensions = {".png", ".jpg", ".jpeg"}

        for category_dir in sorted(root.iterdir()):
            if not category_dir.is_dir():
                continue

            category = category_dir.name

            # Filter by category if specified
            if self.config.categories and category not in self.config.categories:
                continue

            for model_dir in sorted(category_dir.iterdir()):
                if not model_dir.is_dir():
                    continue

                found = self._find_pairs_in_model_dir(
                    model_dir, category, model_dir.name, mesh_extensions, image_extensions
                )
                samples.extend(found)

        logger.info("Scanned %s: found %d valid samples", root, len(samples))
        return samples

    def _find_pairs_in_model_dir(
        self,
        model_dir: Path,
        category: str,
        model_id: str,
        mesh_extensions: set,
        image_extensions: set,
    ) -> List[DataSample]:
        """Find image-mesh pairs within a single model directory."""
        pairs = []

        # Find mesh file
        mesh_path = None
        for ext in mesh_extensions:
            candidates = [
                model_dir / f"model{ext}",
                model_dir / f"mesh{ext}",
                model_dir / f"{model_id}{ext}",
            ]
            # Also check for any file with matching extension
            candidates.extend(model_dir.glob(f"*{ext}"))
            for candidate in candidates:
                if candidate.is_file():
                    mesh_path = candidate
                    break
            if mesh_path:
                break

        if not mesh_path:
            return pairs

        # Find image files
        images_dir = model_dir / "images"
        image_paths = []

        if images_dir.is_dir():
            for ext in image_extensions:
                image_paths.extend(sorted(images_dir.glob(f"*{ext}")))
        else:
            # Flat structure: images in model dir
            for ext in image_extensions:
                image_paths.extend(sorted(model_dir.glob(f"*{ext}")))

        # Load optional metadata
        metadata = self._load_metadata(model_dir)

        for img_path in image_paths:
            pairs.append(DataSample(
                image_path=img_path,
                mesh_path=mesh_path,
                category=category,
                model_id=model_id,
                metadata=metadata,
            ))

        return pairs

    def _load_metadata(self, model_dir: Path) -> Dict[str, Any]:
        """Load metadata.json if present."""
        meta_path = model_dir / "metadata.json"
        if meta_path.is_file():
            try:
                with open(meta_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Failed to load metadata from %s: %s", meta_path, e)
        return {}

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Tuple[Image.Image, MeshData, DataSample]:
        """Load and return an image-mesh pair."""
        sample = self.samples[index]

        image = self._load_image(sample.image_path)
        mesh = self._load_mesh(sample.mesh_path)

        if self.augmentor:
            image = self.augmentor.augment(image)

        return image, mesh, sample

    def _load_image(self, path: Path) -> Image.Image:
        """Load and preprocess an image."""
        image = Image.open(path).convert("RGB")
        size = self.config.image_size
        if image.size != (size, size):
            image = image.resize((size, size), Image.LANCZOS)
        return image

    def _load_mesh(self, path: Path) -> MeshData:
        """Load mesh from OBJ/GLB/STL/PLY file."""
        ext = path.suffix.lower()

        if ext == ".obj":
            return self._load_obj(path)
        elif ext == ".ply":
            return self._load_ply(path)
        else:
            # For GLB/STL, try trimesh if available, else return empty
            return self._load_with_trimesh(path)

    def _load_obj(self, path: Path) -> MeshData:
        """Parse a Wavefront OBJ file."""
        vertices = []
        faces = []

        with open(path, "r", errors="replace") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                if parts[0] == "v" and len(parts) >= 4:
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif parts[0] == "f":
                    # Handle face indices (1-based, may include texture/normal refs)
                    face_verts = []
                    for p in parts[1:]:
                        idx = int(p.split("/")[0]) - 1  # Convert to 0-based
                        face_verts.append(idx)
                    # Triangulate polygons
                    for i in range(1, len(face_verts) - 1):
                        faces.append([face_verts[0], face_verts[i], face_verts[i + 1]])

        verts = np.array(vertices, dtype=np.float32) if vertices else np.zeros((0, 3), dtype=np.float32)
        fcs = np.array(faces, dtype=np.int64) if faces else np.zeros((0, 3), dtype=np.int64)

        return MeshData(
            vertices=verts,
            faces=fcs,
            vertex_count=len(verts),
            face_count=len(fcs),
        )

    def _load_ply(self, path: Path) -> MeshData:
        """Parse a PLY file (ASCII format)."""
        vertices = []
        faces = []

        with open(path, "r", errors="replace") as f:
            # Parse header
            vertex_count = 0
            face_count = 0
            in_header = True

            for line in f:
                line = line.strip()
                if in_header:
                    if line.startswith("element vertex"):
                        vertex_count = int(line.split()[-1])
                    elif line.startswith("element face"):
                        face_count = int(line.split()[-1])
                    elif line == "end_header":
                        in_header = False
                        break

            # Read vertices
            for _ in range(vertex_count):
                parts = f.readline().strip().split()
                if len(parts) >= 3:
                    vertices.append([float(parts[0]), float(parts[1]), float(parts[2])])

            # Read faces
            for _ in range(face_count):
                parts = f.readline().strip().split()
                if len(parts) >= 4:
                    n = int(parts[0])
                    indices = [int(parts[i + 1]) for i in range(n)]
                    # Triangulate
                    for i in range(1, len(indices) - 1):
                        faces.append([indices[0], indices[i], indices[i + 1]])

        verts = np.array(vertices, dtype=np.float32) if vertices else np.zeros((0, 3), dtype=np.float32)
        fcs = np.array(faces, dtype=np.int64) if faces else np.zeros((0, 3), dtype=np.int64)

        return MeshData(
            vertices=verts,
            faces=fcs,
            vertex_count=len(verts),
            face_count=len(fcs),
        )

    def _load_with_trimesh(self, path: Path) -> MeshData:
        """Load mesh using trimesh library (for GLB/STL)."""
        try:
            import trimesh
            mesh = trimesh.load(str(path), force="mesh")
            return MeshData(
                vertices=np.array(mesh.vertices, dtype=np.float32),
                faces=np.array(mesh.faces, dtype=np.int64),
                vertex_count=len(mesh.vertices),
                face_count=len(mesh.faces),
            )
        except ImportError:
            logger.warning("trimesh not installed, cannot load %s", path.suffix)
            return MeshData(
                vertices=np.zeros((0, 3), dtype=np.float32),
                faces=np.zeros((0, 3), dtype=np.int64),
                vertex_count=0,
                face_count=0,
            )
        except Exception as e:
            logger.warning("Failed to load mesh %s: %s", path, e)
            return MeshData(
                vertices=np.zeros((0, 3), dtype=np.float32),
                faces=np.zeros((0, 3), dtype=np.int64),
                vertex_count=0,
                face_count=0,
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Return dataset statistics."""
        categories: Dict[str, int] = {}
        for sample in self.samples:
            categories[sample.category] = categories.get(sample.category, 0) + 1

        return {
            "split": self.split.value,
            "total_samples": len(self.samples),
            "categories": categories,
            "num_categories": len(categories),
        }


def create_data_loaders(
    config: FinetuningConfig,
) -> Dict[DatasetSplit, ShapeNetDataset]:
    """Create train/val/test dataset instances.

    Returns:
        Dictionary mapping DatasetSplit to ShapeNetDataset instances.
    """
    loaders = {}
    for split in DatasetSplit:
        dataset = ShapeNetDataset(config=config, split=split)
        loaders[split] = dataset
        logger.info(
            "Created %s loader: %d samples", split.value, len(dataset)
        )

    return loaders
