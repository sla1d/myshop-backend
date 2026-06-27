"""Storage service — S3/MinIO file storage abstraction."""
import logging
import uuid
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import settings

logger = logging.getLogger("myshop.storage")

# Allowed MIME types
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class StorageService:
    """S3/MinIO compatible file storage."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy-init S3 client."""
        if self._client is not None:
            return self._client

        endpoint_url = settings.S3_ENDPOINT or None
        aws_access_key = settings.S3_ACCESS_KEY
        aws_secret_key = settings.S3_SECRET_KEY

        if not aws_access_key or not aws_secret_key:
            logger.warning("S3 credentials not configured, storage disabled")
            return None

        try:
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=settings.S3_REGION,
                config=BotoConfig(
                    s3={"addressing_style": "path"},
                    signature_version="s3v4",
                ),
            )
            logger.info("S3 client initialized: endpoint=%s, bucket=%s", endpoint_url, settings.S3_BUCKET)
            return self._client
        except Exception as e:
            logger.error("Failed to init S3 client: %s", e)
            return None

    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = "image/jpeg",
        tenant_id: int | None = None,
        folder: str = "uploads",
    ) -> Optional[dict]:
        """Upload file to S3/MinIO.

        Returns dict with url and key, or None on failure.
        """
        client = self._get_client()
        if not client:
            return None

        # Validate
        if content_type not in ALLOWED_TYPES:
            raise ValueError(f"Allowed types: {', '.join(ALLOWED_TYPES)}")
        if len(file_data) > MAX_FILE_SIZE:
            raise ValueError(f"Max file size: {MAX_FILE_SIZE // (1024*1024)}MB")

        # Generate unique key
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        unique_name = f"{uuid.uuid4().hex}.{ext}"

        # Build key path
        key_parts = [folder]
        if tenant_id:
            key_parts.append(str(tenant_id))
        key_parts.append(unique_name)
        key = "/".join(key_parts)

        try:
            client.put_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
                Body=file_data,
                ContentType=content_type,
                ACL="public-read",
            )

            # Build URL
            if settings.S3_ENDPOINT:
                url = f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{key}"
            else:
                url = f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{key}"

            logger.info("File uploaded: %s", key)
            return {"url": url, "key": key, "filename": unique_name}
        except Exception as e:
            logger.error("Upload failed: %s", e)
            return None

    async def delete_file(self, key: str) -> bool:
        """Delete file from S3/MinIO."""
        client = self._get_client()
        if not client:
            return False

        try:
            client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
            logger.info("File deleted: %s", key)
            return True
        except Exception as e:
            logger.error("Delete failed: %s", e)
            return False

    async def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """Generate pre-signed URL for private files."""
        client = self._get_client()
        if not client:
            return None

        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.S3_BUCKET, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error("Presigned URL generation failed: %s", e)
            return None


# Singleton
storage = StorageService()
