from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import psycopg2

from ..config import Settings
from ..config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TaskEntity:
    """Task generation entity."""
    task_id: str
    status: str
    result_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TaskRepositoryInterface(ABC):
    """Task repository interface (Dependency Inversion)."""

    @abstractmethod
    def create(self, task_id: str, status: str) -> None:
        pass

    @abstractmethod
    def update_status(self, task_id: str, status: str, result_path: Optional[str] = None, error_msg: Optional[str] = None) -> None:
        pass


class TaskRepository(TaskRepositoryInterface):
    """
    PostgreSQL repository implementation.
    Updates the Kotlin service's tasks table (id UUID PK, status, s3_output_key).
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(self.settings.database_url)

    def _init_db(self) -> None:
        """Verify DB connectivity (table is managed by Kotlin service Liquibase)."""
        conn = self._get_connection()
        conn.close()
        logger.info("Database initialized.")

    def create(self, task_id: str, status: str) -> None:
        """No-op: task row is created by Kotlin service. We only update status."""
        pass

    def update_status(self, task_id: str, status: str, result_path: Optional[str] = None, error_msg: Optional[str] = None) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        if result_path:
            cur.execute(
                "UPDATE tasks SET status=%s, s3_output_key=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s::uuid",
                (status, result_path, task_id)
            )
        elif error_msg:
            cur.execute(
                "UPDATE tasks SET status=%s, error_message=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s::uuid",
                (status, error_msg[:1000], task_id)
            )
        else:
            cur.execute(
                "UPDATE tasks SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s::uuid",
                (status, task_id)
            )
        conn.commit()
        cur.close()
        conn.close()

    def save_generation_metrics(self, task_id: str, metrics: Dict[str, any]) -> None:
        """Save generation quality metrics to generation_metrics table."""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO generation_metrics (
                    task_id, chamfer_distance, iou_3d, f_score, normal_consistency,
                    vertices, faces, inference_time_sec, is_mock
                ) VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (task_id) DO UPDATE SET
                    chamfer_distance = EXCLUDED.chamfer_distance,
                    iou_3d = EXCLUDED.iou_3d,
                    f_score = EXCLUDED.f_score,
                    normal_consistency = EXCLUDED.normal_consistency,
                    vertices = EXCLUDED.vertices,
                    faces = EXCLUDED.faces,
                    inference_time_sec = EXCLUDED.inference_time_sec,
                    is_mock = EXCLUDED.is_mock
                """,
                (
                    task_id,
                    metrics.get("chamfer_distance"),
                    metrics.get("iou_3d"),
                    metrics.get("f_score"),
                    metrics.get("normal_consistency"),
                    metrics.get("vertices"),
                    metrics.get("faces"),
                    metrics.get("inference_time_sec"),
                    metrics.get("is_mock", False),
                ),
            )
            conn.commit()
            logger.info("Saved generation metrics for task %s", task_id)
        except Exception as e:
            conn.rollback()
            logger.error("Failed to save metrics for task %s: %s", task_id, e)
            raise
        finally:
            cur.close()
            conn.close()

    def get_app_settings(self) -> Dict[str, str]:
        """Read runtime ML settings from app_settings table."""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT setting_key, setting_value FROM app_settings")
            return {row[0]: row[1] for row in cur.fetchall()}
        except Exception as e:
            logger.warning("Could not read app_settings: %s", e)
            return {}
        finally:
            cur.close()
            conn.close()
