from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, Literal


class Settings(BaseSettings):
    """
    ModelForge ML Worker configuration.
    Validates environment variables at startup.
    """

    # === Kafka ===
    kafka_bootstrap_servers: str = Field(
        default="kafka:9092",
        description="Kafka bootstrap servers"
    )
    kafka_topic: str = Field(
        default="modelforge.generation.requests",
        description="Kafka topic for tasks"
    )
    kafka_group_id: str = Field(
        default="modelforge.ml-workers",
        description="Kafka consumer group ID"
    )

    # === Database ===
    database_url: str = Field(
        default="postgresql://modelforge:modelforge_secret@postgres:5432/modelforge_db",
        description="PostgreSQL connection URL"
    )

    # === S3 Storage ===
    s3_endpoint: str = Field(
        default="minio:9000",
        description="S3-compatible storage endpoint"
    )
    s3_access_key: str = Field(
        default="modelforge_admin",
        description="S3 access key"
    )
    s3_secret_key: str = Field(
        default="modelforge_secret",
        description="S3 secret key"
    )
    s3_bucket: str = Field(
        default="models-output",
        description="S3 bucket name"
    )

    # === ML Service ===
    ml_mock_mode: bool = Field(
        default=True,
        description="Use mock service for testing (no real ML inference)"
    )
    ml_mock_delay: float = Field(
        default=5.0,
        description="Mock processing delay in seconds"
    )

    tripsr_device: str = Field(
        default="cuda:0",
        description="Preferred device for TripoSR: 'cuda:0' or 'cpu'"
    )
    tripsr_model_path: Optional[str] = Field(
        default=None,
        description="Local path to TripoSR model weights (optional)"
    )

    # === Preprocessing ===
    preprocess_image_size: int = Field(
        default=512,
        description="Target square image size for ML inference"
    )

    # === Fine-tuning ===
    finetuning_dataset_root: str = Field(
        default="data/shapenet",
        description="Root path to training dataset (ShapeNet/Objaverse)"
    )
    finetuning_dataset_type: str = Field(
        default="shapenet",
        description="Dataset type: 'shapenet' or 'objaverse'"
    )
    finetuning_batch_size: int = Field(
        default=4,
        description="Training batch size"
    )
    finetuning_image_size: int = Field(
        default=512,
        description="Image size for fine-tuning"
    )
    finetuning_seed: int = Field(
        default=42,
        description="Random seed for reproducibility"
    )

    # === Training ===
    training_num_epochs: int = Field(
        default=50,
        description="Number of training epochs"
    )
    training_learning_rate: float = Field(
        default=1e-4,
        description="Initial learning rate"
    )
    training_lr_schedule: str = Field(
        default="cosine",
        description="LR schedule: 'cosine', 'step', or 'constant'"
    )
    training_warmup_epochs: int = Field(
        default=3,
        description="Number of warmup epochs"
    )
    training_checkpoint_dir: str = Field(
        default="checkpoints/triposr",
        description="Directory for saving training checkpoints"
    )
    training_early_stopping_patience: int = Field(
        default=10,
        description="Epochs without improvement before early stopping (0=disabled)"
    )
    training_chamfer_weight: float = Field(
        default=1.0,
        description="Weight for Chamfer distance loss"
    )
    training_edge_weight: float = Field(
        default=0.1,
        description="Weight for edge length regularization loss"
    )
    training_laplacian_weight: float = Field(
        default=0.05,
        description="Weight for Laplacian smoothing loss"
    )

    # === Weight Management ===
    model_version: str = Field(
        default="base",
        description="Active model version: 'base' or a registered fine-tuned version ID"
    )
    checkpoint_s3_prefix: str = Field(
        default="checkpoints/triposr",
        description="S3 prefix for storing/loading model checkpoints"
    )

    # === Experiment flags ===
    experiment_collect_metrics: bool = Field(
        default=True,
        description="Calculate scientific metrics (Chamfer, UV-stretch, etc.)"
    )

    # === Logging ===
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: Literal["json", "text"] = Field(
        default="text",
        description="Log output format: 'json' for Loki/Grafana, 'text' for console"
    )
    service_name: str = Field(
        default="modelforge-ml-worker",
        description="Service name for log attribution"
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        # Allow uppercase env var names: LOG_LEVEL instead of log_level
        alias_generator = lambda s: s.upper()
        populate_by_name = True

    @validator('tripsr_device')
    def validate_device(cls, v):
        if v not in ('cpu', 'cuda', 'cuda:0', 'cuda:1'):
            raise ValueError('Device must be cpu or cuda[:N]')
        return v


# Global singleton for convenience
settings = Settings()
