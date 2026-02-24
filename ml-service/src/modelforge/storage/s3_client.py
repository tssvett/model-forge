import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError

from ..config import Settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """
    Сервис для работы с S3-совместимым хранилищем.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = self._create_client()
        self._ensure_bucket_exists()

    def _create_client(self):
        return boto3.client(
            's3',
            endpoint_url=f'http://{self.settings.s3_endpoint}',
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            config=boto3.session.Config(signature_version='s3v4')
        )

    def _ensure_bucket_exists(self) -> None:
        """Создает бакет если не существует."""
        try:
            self._client.head_bucket(Bucket=self.settings.s3_bucket)
            logger.info(f"Bucket '{self.settings.s3_bucket}' already exists.")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.info(f"Creating bucket '{self.settings.s3_bucket}'...")
                self._client.create_bucket(Bucket=self.settings.s3_bucket)
                logger.info(f"Bucket '{self.settings.s3_bucket}' created.")
            else:
                raise

    def upload_bytes(self, key: str, data: bytes) -> str:
        """Загружает байты в S3, возвращает s3:// путь."""
        self._client.put_object(
            Bucket=self.settings.s3_bucket,
            Key=key,
            Body=data
        )
        path = f"s3://{self.settings.s3_bucket}/{key}"
        logger.info(f"Uploaded file to {path}")
        return path

    def download_file(self, s3_path: str) -> bytes:
        """Скачивает файл из S3 по пути s3://bucket/key."""
        if not s3_path.startswith("s3://"):
            raise ValueError(f"Invalid S3 path: {s3_path}")

        parts = s3_path[5:].split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""

        response = self._client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
