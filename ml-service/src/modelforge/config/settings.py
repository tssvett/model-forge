from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional


class Settings(BaseSettings):
    """
    Конфигурация приложения ModelForge ML Worker.
    Валидация переменных окружения при старте.
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

    # === Experiment flags ===
    experiment_collect_metrics: bool = Field(
        default=True,
        description="Calculate scientific metrics (Chamfer, UV-stretch, etc.)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @validator('tripsr_device')
    def validate_device(cls, v):
        if v not in ('cpu', 'cuda', 'cuda:0', 'cuda:1'):
            raise ValueError('Device must be cpu or cuda[:N]')
        return v


# Глобальный инстанс для удобства
settings = Settings()
