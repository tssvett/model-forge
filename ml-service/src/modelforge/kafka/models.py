"""Pydantic models for Kafka message contracts."""

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class InputData(BaseModel):
    """Input data for a generation task."""

    s3_path: str = Field(..., description="Path to the input image in MinIO")
    format: Optional[str] = Field(
        default=None,
        description="Image format (jpg, png, webp)",
    )

    @field_validator("s3_path")
    @classmethod
    def validate_s3_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("s3_path must not be empty")
        return v.strip()


class ProcessingParams(BaseModel):
    """Parameters controlling the generation pipeline."""

    output_format: str = Field(
        default="glb",
        description="Output 3D model format",
    )
    remove_background: bool = Field(
        default=True,
        description="Whether to remove background from the input image",
    )
    texture_quality: Optional[str] = Field(
        default=None,
        description="Texture quality: low, medium, high",
    )

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        allowed = {"obj", "glb", "usdz", "stl", "ply"}
        v = v.lower().strip()
        if v not in allowed:
            raise ValueError(f"output_format must be one of {allowed}, got '{v}'")
        return v


class TaskRequest(BaseModel):
    """
    Kafka message contract for a 3D model generation task.

    Supports both camelCase (from Kotlin service) and snake_case formats
    via field aliases.
    """

    task_id: str = Field(..., description="Unique task identifier (UUID)")
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier",
    )
    input: InputData = Field(..., description="Input data specification")
    params: ProcessingParams = Field(
        default_factory=ProcessingParams,
        description="Processing parameters",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Task creation timestamp (ISO 8601)",
    )

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        if not v or v == "unknown":
            raise ValueError("task_id must be a valid identifier")
        return v

    @classmethod
    def from_kafka_message(cls, raw: dict) -> "TaskRequest":
        """
        Parse a raw Kafka message dict into a TaskRequest.

        Handles both snake_case (legacy) and camelCase (Kotlin service) formats.
        """
        task_id = raw.get("task_id") or raw.get("taskId", "unknown")

        # Normalize input block
        input_data = raw.get("input")
        if input_data and "s3_path" in input_data:
            input_block = input_data
        else:
            s3_path = raw.get("s3InputKey") or raw.get("s3_input_key", "")
            input_block = {"s3_path": s3_path}

        # Normalize params block
        params_data = raw.get("params") or {}
        params_block = {
            "output_format": params_data.get("output_format", "glb"),
            "remove_background": params_data.get("remove_background", True),
            "texture_quality": params_data.get("texture_quality"),
        }

        return cls(
            task_id=task_id,
            user_id=raw.get("user_id") or raw.get("userId"),
            input=InputData(**input_block),
            params=ProcessingParams(**params_block),
            created_at=raw.get("created_at") or raw.get("createdAt"),
        )
