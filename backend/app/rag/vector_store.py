from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.core.exceptions import ExternalServiceException


@dataclass(slots=True)
class VectorSearchHit:
    """
    Qdrant 向量检索结果。
    """

    chunk_id: UUID
    document_id: UUID
    score: float
    payload: dict[str, Any]


class QdrantVectorStore:
    """
    Qdrant 向量存储。

    负责：
    - 确保 collection 存在
    - upsert chunk vectors
    - vector search

    不负责：
    - 生成 embedding
    - 查询 PostgreSQL 文档详情
    - 拼接最终引用来源
    """

    def __init__(
        self,
        *,
        url: str,
        collection_name: str,
        vector_size: int,
    ) -> None:
        self.url = url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = QdrantClient(url=url)

    def ensure_collection(self) -> None:
        try:
            existing = self.client.collection_exists(
                collection_name=self.collection_name,
            )

            if existing:
                return

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self.vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
        except Exception as exc:
            raise ExternalServiceException(
                code="QDRANT_COLLECTION_INIT_FAILED",
                message="Qdrant collection 初始化失败",
                data={
                    "collection": self.collection_name,
                    "url": self.url,
                    "error": str(exc),
                },
            ) from exc

    def upsert_chunks(
        self,
        *,
        points: list[tuple[UUID, list[float], dict[str, Any]]],
    ) -> None:
        """
        写入向量点。

        points item:
        - point_id: 使用 knowledge_chunk.id
        - vector: embedding
        - payload: chunk metadata
        """
        if not points:
            return

        self.ensure_collection()

        qdrant_points = [
            qdrant_models.PointStruct(
                id=str(point_id),
                vector=vector,
                payload=payload,
            )
            for point_id, vector, payload in points
        ]

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=qdrant_points,
            )
        except Exception as exc:
            raise ExternalServiceException(
                code="QDRANT_UPSERT_FAILED",
                message="Qdrant 向量写入失败",
                data={
                    "collection": self.collection_name,
                    "point_count": len(points),
                    "error": str(exc),
                },
            ) from exc

    def search(
        self,
        *,
        tenant_id: UUID,
        query_vector: list[float],
        top_k: int,
    ) -> list[VectorSearchHit]:
        if not query_vector:
            return []

        self.ensure_collection()

        query_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="tenant_id",
                    match=qdrant_models.MatchValue(value=str(tenant_id)),
                )
            ]
        )

        try:
            if hasattr(self.client, "search"):
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                    query_filter=query_filter,
                )
            else:
                query_response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=top_k,
                    query_filter=query_filter,
                    with_payload=True,
                    with_vectors=False,
                )
                results = query_response.points
        except Exception as exc:
            raise ExternalServiceException(
                code="QDRANT_SEARCH_FAILED",
                message="Qdrant 向量检索失败",
                data={
                    "collection": self.collection_name,
                    "top_k": top_k,
                    "error": str(exc),
                },
            ) from exc

        hits: list[VectorSearchHit] = []

        for item in results:
            payload = item.payload or {}

            chunk_id = payload.get("chunk_id") or item.id
            document_id = payload.get("document_id")

            if not document_id:
                continue

            hits.append(
                VectorSearchHit(
                    chunk_id=UUID(str(chunk_id)),
                    document_id=UUID(str(document_id)),
                    score=float(item.score),
                    payload=payload,
                )
            )

        return hits