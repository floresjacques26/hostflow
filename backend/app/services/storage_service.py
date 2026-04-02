"""
Pluggable file storage abstraction.

Providers:
  local   — saves files to a local directory; useful for development
  s3      — S3-compatible API (AWS S3 or Cloudflare R2)

Usage:
  storage = get_storage()
  key = await storage.upload(data=bytes, key="media/2024/01/file.jpg", content_type="image/jpeg")
  url = await storage.get_url(key)
  await storage.delete(key)

The key is always relative (no leading slash).
For the local provider, `get_url()` returns an HTTP URL served by FastAPI's StaticFiles.
For S3 with a CDN base URL configured, `get_url()` returns the CDN URL.
For S3 without CDN, `get_url()` returns a pre-signed URL valid for 1 hour.
"""
import asyncio
import logging
import os
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Abstract interface ────────────────────────────────────────────────────────

class StorageProvider(ABC):
    @abstractmethod
    async def upload(
        self,
        data: bytes,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes; returns the storage key."""

    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Return a publicly accessible URL for the key."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete the object. Silent if not found."""


# ── Key generation helper ─────────────────────────────────────────────────────

def make_media_key(media_type: str, extension: str) -> str:
    """Generate a unique storage key under media/{type}/{uuid}.{ext}."""
    uid = uuid.uuid4().hex
    return f"media/{media_type}/{uid}.{extension}"


# ── Local provider ────────────────────────────────────────────────────────────

class LocalStorageProvider(StorageProvider):
    def __init__(self, root: str, url_base: str):
        self.root = Path(root)
        self.url_base = url_base.rstrip("/")

    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.debug("LocalStorage: wrote %d bytes → %s", len(data), path)
        return key

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        return f"{self.url_base}/{key}"

    async def delete(self, key: str) -> None:
        path = self.root / key
        if path.exists():
            path.unlink()


# ── S3 / Cloudflare R2 provider ───────────────────────────────────────────────

class S3StorageProvider(StorageProvider):
    """
    Wraps boto3 S3 client in asyncio.to_thread() calls so it doesn't block the
    event loop. Compatible with AWS S3, Cloudflare R2, MinIO, etc.
    """

    def __init__(self):
        import boto3  # import lazily so local-only installs don't need boto3
        self._s3 = boto3.client(
            "s3",
            region_name=settings.storage_s3_region if settings.storage_s3_region != "auto" else None,
            endpoint_url=settings.storage_s3_endpoint_url or None,
            aws_access_key_id=settings.storage_s3_access_key_id,
            aws_secret_access_key=settings.storage_s3_secret_access_key,
        )
        self._bucket = settings.storage_s3_bucket
        self._cdn_base = settings.storage_s3_public_base_url.rstrip("/") if settings.storage_s3_public_base_url else None

    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        def _put():
            self._s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        await asyncio.to_thread(_put)
        logger.debug("S3Storage: uploaded %d bytes → s3://%s/%s", len(data), self._bucket, key)
        return key

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        if self._cdn_base:
            return f"{self._cdn_base}/{key}"

        def _presign():
            return self._s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        return await asyncio.to_thread(_presign)

    async def delete(self, key: str) -> None:
        def _del():
            try:
                self._s3.delete_object(Bucket=self._bucket, Key=key)
            except Exception:
                pass
        await asyncio.to_thread(_del)


# ── Factory ───────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_storage() -> StorageProvider:
    """Return the configured storage provider (singleton)."""
    if settings.storage_provider == "s3":
        logger.info("Storage: using S3 provider (bucket=%s)", settings.storage_s3_bucket)
        return S3StorageProvider()

    logger.info("Storage: using local provider (root=%s)", settings.storage_local_root)
    return LocalStorageProvider(
        root=settings.storage_local_root,
        url_base=settings.storage_local_url_base,
    )
