import boto3
from botocore.exceptions import ClientError

from ..config import Settings
from ..config.logging import get_logger

logger = get_logger(__name__)


class S3StorageService:
    """S3-compatible storage client (MinIO)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = self._create_client()
        self._ensure_bucket_exists()

    def _create_client(self):
        return boto3.client(
            "s3",
            endpoint_url=f"http://{self.settings.s3_endpoint}",
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            config=boto3.session.Config(signature_version="s3v4"),
        )

    def _ensure_bucket_exists(self) -> None:
        """Create the bucket if it does not exist."""
        try:
            self._client.head_bucket(Bucket=self.settings.s3_bucket)
            logger.info("Bucket '%s' already exists.", self.settings.s3_bucket)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.info("Creating bucket '%s'...", self.settings.s3_bucket)
                self._client.create_bucket(Bucket=self.settings.s3_bucket)
                logger.info("Bucket '%s' created.", self.settings.s3_bucket)
            else:
                raise

    def upload_bytes(self, key: str, data: bytes) -> str:
        """Upload bytes to S3 and return the s3:// path."""
        self._client.put_object(
            Bucket=self.settings.s3_bucket,
            Key=key,
            Body=data,
        )
        path = f"s3://{self.settings.s3_bucket}/{key}"
        logger.info("Uploaded file to %s", path)
        return path

    def download_file(self, s3_path: str) -> bytes:
        """Download a file from S3 by s3://bucket/key path or plain key."""
        if s3_path.startswith("s3://"):
            parts = s3_path[5:].split("/", 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""
        else:
            bucket = self.settings.s3_bucket
            key = s3_path

        response = self._client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
