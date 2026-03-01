from __future__ import annotations

import os
from datetime import timedelta
from typing import Iterable

from minio import Minio
import urllib3
import ssl

from src.core.config import settings


_minio_client: Minio | None = None


def get_minio_client() -> Minio:
    global _minio_client
    if _minio_client is None:
        http_client = urllib3.PoolManager(
            timeout=urllib3.Timeout.DEFAULT_TIMEOUT,
            maxsize=10,
            cert_reqs=ssl.CERT_REQUIRED if settings.minio_secure else ssl.CERT_NONE,
        )
        _minio_client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key.get_secret_value(),
            secret_key=settings.minio_secret_key.get_secret_value(),
            secure=settings.minio_secure,
            http_client=http_client,
        )
    return _minio_client


class MinIOService:
    def __init__(self) -> None:
        self.client = get_minio_client()

    def upload_file(
        self,
        bucket: str,
        file_path: str,
        object_name: str | None = None,
        expires_days: int = 7,
    ) -> str:
        if object_name is None:
            object_name = os.path.basename(file_path)

        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

        self.client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path,
        )

        url = self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(days=expires_days),
        )
        return url

    def download_file(self, bucket: str, object_name: str, file_path: str) -> None:
        self.client.fget_object(bucket_name=bucket, object_name=object_name, file_path=file_path)

    def delete_file(self, bucket: str, object_name: str) -> None:
        self.client.remove_object(bucket_name=bucket, object_name=object_name)

    def list_files(self, bucket: str, prefix: str | None = None) -> Iterable[str]:
        for obj in self.client.list_objects(bucket_name=bucket, prefix=prefix or "", recursive=True):
            yield obj.object_name

