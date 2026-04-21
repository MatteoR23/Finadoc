"""S3/MinIO helpers for document download and result upload."""
from __future__ import annotations

import tempfile
from pathlib import Path

import boto3
from botocore.config import Config

from config import S3_ACCESS_KEY, S3_ENDPOINT_URL, S3_SECRET_KEY

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            config=Config(s3={"addressing_style": "path"}),
        )
    return _client


def download_to_tempfile(bucket: str, key: str) -> Path:
    """Download an S3 object to a temporary file and return its path.

    The caller is responsible for deleting the file when done.
    """
    suffix = Path(key).suffix or ".tmp"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    _get_client().download_fileobj(bucket, key, tmp)
    tmp.close()
    return Path(tmp.name)


def upload_bytes(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload raw bytes to an S3 key."""
    import io
    _get_client().upload_fileobj(io.BytesIO(data), bucket, key, ExtraArgs={"ContentType": content_type})
