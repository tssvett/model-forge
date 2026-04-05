from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class InputData(BaseModel):
    """Input data for a generation task."""
    s3_path: str = Field(..., min_length=1)
    format: str = Field(default="jpg")

    @field_validator("s3_path")
    @classmethod
    def validate_s3_path(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("s3_path must not be empty")
        return v


class ProcessingParams(BaseModel):
    """Parameters controlling the generation pipeline."""
    output_format: str = Field(default="glb")
    remove_background: bool = Field(default=True)
    texture_quality: str = Field(default="high")

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        allowed = {"glb", "obj", "stl", "ply"}
        if v.lower() not in allowed:
            raise ValueError(f"output_format must be one of {allowed}, got '{v}'")
        return v.lower()


class TaskRequest(BaseModel):
    """Kafka message contract for a generation task."""
    task_id: str = Field(..., min_length=1)
    user_id: Optional[str] = None
    input: InputData
    params: ProcessingParams = Field(default_factory=ProcessingParams)
    created_at: Optional[datetime] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v
