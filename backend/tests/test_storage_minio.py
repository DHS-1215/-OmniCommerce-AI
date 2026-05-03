from __future__ import annotations

from app.storage.minio_storage import MinIOStorageClient


def test_minio_storage_client_can_be_initialized() -> None:
    client = MinIOStorageClient(
        endpoint="localhost:9000",
        access_key="test_access",
        secret_key="test_secret",
        bucket_name="test-bucket",
        secure=False,
    )

    assert client.endpoint == "localhost:9000"
    assert client.bucket_name == "test-bucket"