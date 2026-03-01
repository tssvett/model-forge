from abc import ABC, abstractmethod
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import psycopg2

from ..config import Settings
from ..config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TaskEntity:
    """Entity для задачи генерации."""
    task_id: str
    status: str
    result_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TaskRepositoryInterface(ABC):
    """Интерфейс репозитория задач (Dependency Inversion)."""

    @abstractmethod
    def create(self, task_id: str, status: str) -> None:
        pass

    @abstractmethod
    def update_status(self, task_id: str, status: str, result_path: Optional[str] = None) -> None:
        pass


class TaskRepository(TaskRepositoryInterface):
    """
    Реализация репозитория для PostgreSQL.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(self.settings.database_url)

    def _init_db(self) -> None:
        """Создает таблицу задач если не существует."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id VARCHAR(255) PRIMARY KEY,
                status VARCHAR(50),
                result_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized.")

    def create(self, task_id: str, status: str) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tasks (task_id, status) VALUES (%s, %s) ON CONFLICT (task_id) DO NOTHING",
            (task_id, status)
        )
        conn.commit()
        cur.close()
        conn.close()

    def update_status(self, task_id: str, status: str, result_path: Optional[str] = None) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        if result_path:
            cur.execute(
                "UPDATE tasks SET status=%s, result_path=%s, updated_at=CURRENT_TIMESTAMP WHERE task_id=%s",
                (status, result_path, task_id)
            )
        else:
            cur.execute(
                "UPDATE tasks SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE task_id=%s",
                (status, task_id)
            )
        conn.commit()
        cur.close()
        conn.close()
