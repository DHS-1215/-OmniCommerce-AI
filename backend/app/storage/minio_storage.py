from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.exceptions import ExternalServiceException


@dataclass(slots=True)
class StoredObject:
    """
    MinIO 对象存储结果。
    """

    bucket: str
    object_key: str
    size: int
    content_type: str | None = None


class MinIOStorageClient:
    """
    MinIO 文档对象存储客户端。

    职责：
    - 确保 bucket 存在
    - 上传原始文档字节
    - 删除对象，用于异常回滚时做 best-effort cleanup

    注意：
    这里不负责解析文档，也不负责写数据库。
    """

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure: bool = False,
    ) -> None:
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def ensure_bucket(self) -> None:
        try:
            if self.client.bucket_exists(self.bucket_name):
                return

            self.client.make_bucket(self.bucket_name)
        except S3Error as exc:
            raise ExternalServiceException(
                code="MINIO_BUCKET_INIT_FAILED",
                message="MinIO bucket 初始化失败",
                data={
                    "bucket": self.bucket_name,
                    "endpoint": self.endpoint,
                    "error": str(exc),
                },
            ) from exc
        except Exception as exc:
            raise ExternalServiceException(
                code="MINIO_BUCKET_INIT_FAILED",
                message="MinIO bucket 初始化失败",
                data={
                    "bucket": self.bucket_name,
                    "endpoint": self.endpoint,
                    "error": str(exc),
                },
            ) from exc

    def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        """
        上传字节内容到 MinIO。

        object_key 示例：
        knowledge/{tenant_id}/{uuid}_{filename}
        """

        if not content:
            raise ExternalServiceException(
                code="MINIO_EMPTY_OBJECT",
                message="MinIO 不允许上传空对象",
                data={
                    "bucket": self.bucket_name,
                    "object_key": object_key,
                },
            )

        self.ensure_bucket()

        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=BytesIO(content),
                length=len(content),
                content_type=content_type or "application/octet-stream",
            )
        except S3Error as exc:
            raise ExternalServiceException(
                code="MINIO_UPLOAD_FAILED",
                message="MinIO 文件上传失败",
                data={
                    "bucket": self.bucket_name,
                    "object_key": object_key,
                    "endpoint": self.endpoint,
                    "error": str(exc),
                },
            ) from exc
        except Exception as exc:
            raise ExternalServiceException(
                code="MINIO_UPLOAD_FAILED",
                message="MinIO 文件上传失败",
                data={
                    "bucket": self.bucket_name,
                    "object_key": object_key,
                    "endpoint": self.endpoint,
                    "error": str(exc),
                },
            ) from exc

        return StoredObject(
            bucket=self.bucket_name,
            object_key=object_key,
            size=len(content),
            content_type=content_type,
        )

    def delete_object_safely(self, *, object_key: str) -> None:
        """
        best-effort 删除对象。

        用于数据库入库失败时清理已经上传到 MinIO 的原始文件。
        清理失败不应该覆盖原始业务异常。
        """

        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
            )
        except Exception:
            return