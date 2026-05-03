from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence
from uuid import UUID

from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExternalServiceException
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.rag.keyword_extractor import KeywordExtractor


@dataclass(slots=True)
class KeywordSearchHit:
    """
    关键词检索结果。
    """

    chunk_id: UUID
    document_id: UUID
    score: float
    payload: dict[str, Any]


class KeywordStore(ABC):
    """
    关键词检索抽象接口。

    HybridRetriever 只能依赖这个抽象，不允许依赖具体实现。
    """

    @abstractmethod
    async def search(
        self,
        *,
        tenant_id: UUID,
        query: str,
        top_k: int,
        document_ids: Sequence[UUID] | None = None,
        status_filter: Sequence[str] | None = None,
    ) -> list[KeywordSearchHit]:
        """
        执行关键词检索。

        document_ids / status_filter 是为了企业级过滤预留。
        HybridRetriever 当前不传这些参数也不影响主流程。
        """


class SimpleKeywordStore(KeywordStore):
    """
    轻量关键词检索实现。

    当前版本直接基于 PostgreSQL 中的 knowledge_chunk 做轻量检索。
    这是 fallback 实现，不是完整 OpenSearch 检索。
    """

    def __init__(
        self,
        *,
        db_session: AsyncSession,
        keyword_extractor: KeywordExtractor | None = None,
    ) -> None:
        self.db_session = db_session
        self.keyword_extractor = keyword_extractor or KeywordExtractor()

    async def search(
        self,
        *,
        tenant_id: UUID,
        query: str,
        top_k: int,
        document_ids: Sequence[UUID] | None = None,
        status_filter: Sequence[str] | None = None,
    ) -> list[KeywordSearchHit]:
        query_keywords = self.keyword_extractor.extract(query, max_keywords=20)

        if not query_keywords:
            return []

        effective_status = list(status_filter or ["indexed", "active"])

        stmt = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(KnowledgeChunk.tenant_id == tenant_id)
            .where(KnowledgeDocument.tenant_id == tenant_id)
            .where(KnowledgeChunk.deleted_at.is_(None))
            .where(KnowledgeDocument.deleted_at.is_(None))
            .where(KnowledgeDocument.status.in_(effective_status))
            .limit(500)
        )

        if document_ids:
            stmt = stmt.where(KnowledgeChunk.document_id.in_(list(document_ids)))

        result = await self.db_session.execute(stmt)
        rows = result.all()

        hits: list[KeywordSearchHit] = []

        for chunk, document in rows:
            score = self._score_chunk(
                query_keywords=query_keywords,
                content=chunk.content or "",
                keywords_json=chunk.keywords_json,
            )

            if score <= 0:
                continue

            hits.append(
                KeywordSearchHit(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    score=score,
                    payload={
                        "chunk_id": str(chunk.id),
                        "document_id": str(chunk.document_id),
                        "document_title": document.title,
                        "document_status": document.status,
                        "chunk_no": chunk.chunk_no,
                        "page_no": chunk.page_no,
                        "section_title": chunk.section_title,
                        "content": chunk.content,
                        "keywords_json": chunk.keywords_json,
                        "metadata_json": chunk.metadata_json,
                        "keyword_store": "simple",
                    },
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)

        return hits[:top_k]

    @staticmethod
    def _score_chunk(
        *,
        query_keywords: list[str],
        content: str,
        keywords_json: Any,
    ) -> float:
        content_lower = content.lower()

        chunk_keywords: set[str] = set()

        if isinstance(keywords_json, list):
            chunk_keywords = {str(item).lower() for item in keywords_json}
        elif isinstance(keywords_json, dict):
            values = keywords_json.get("keywords") or []
            if isinstance(values, list):
                chunk_keywords = {str(item).lower() for item in values}

        score = 0.0

        for keyword in query_keywords:
            normalized = keyword.lower()

            if normalized in chunk_keywords:
                score += 2.0

            if normalized in content_lower:
                score += 1.0

        return score


class OpenSearchKeywordStore(KeywordStore):
    """
    OpenSearch 关键词检索实现。

    能力：
    - chunk 索引写入
    - BM25 / match 检索
    - tenant_id 过滤
    - document status 过滤
    - document_id 过滤
    """

    def __init__(
        self,
        *,
        url: str,
        index_name: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.url = url
        self.index_name = index_name

        http_auth = None
        if username and password:
            http_auth = (username, password)

        self.client = OpenSearch(
            hosts=[url],
            http_auth=http_auth,
            use_ssl=url.startswith("https://"),
            verify_certs=False,
            timeout=10,
            max_retries=2,
            retry_on_timeout=True,
        )

    def ensure_index(self) -> None:
        """
        确保 OpenSearch index 存在。
        """

        try:
            if self.client.indices.exists(index=self.index_name):
                return

            self.client.indices.create(
                index=self.index_name,
                body={
                    "settings": {
                        "index": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                        }
                    },
                    "mappings": {
                        "properties": {
                            "tenant_id": {"type": "keyword"},
                            "document_id": {"type": "keyword"},
                            "document_no": {"type": "keyword"},
                            "document_title": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                },
                            },
                            "document_status": {"type": "keyword"},
                            "chunk_id": {"type": "keyword"},
                            "chunk_no": {"type": "keyword"},
                            "content": {"type": "text"},
                            "keywords": {"type": "keyword"},
                            "page_no": {"type": "integer"},
                            "section_title": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                },
                            },
                            "metadata_json": {"type": "object", "enabled": False},
                            "created_at": {"type": "date"},
                        }
                    },
                },
            )
        except Exception as exc:
            raise ExternalServiceException(
                code="OPENSEARCH_INDEX_INIT_FAILED",
                message="OpenSearch index 初始化失败",
                data={
                    "url": self.url,
                    "index": self.index_name,
                    "error": str(exc),
                },
            ) from exc

    def upsert_chunks(
        self,
        *,
        chunks: Sequence[KnowledgeChunk],
        document: KnowledgeDocument,
    ) -> None:
        """
        将 chunk 写入 OpenSearch。

        这里使用 chunk.id 作为 OpenSearch document id，
        方便 PostgreSQL chunk、Qdrant point、OpenSearch document 三者稳定关联。
        """

        if not chunks:
            return

        self.ensure_index()

        from opensearchpy.helpers import bulk

        actions = []

        for chunk in chunks:
            actions.append(
                {
                    "_op_type": "index",
                    "_index": self.index_name,
                    "_id": str(chunk.id),
                    "_source": {
                        "tenant_id": str(chunk.tenant_id),
                        "document_id": str(chunk.document_id),
                        "document_no": document.document_no,
                        "document_title": document.title,
                        "document_status": document.status,
                        "chunk_id": str(chunk.id),
                        "chunk_no": str(chunk.chunk_no),
                        "content": chunk.content,
                        "keywords": self._normalize_keywords(chunk.keywords_json),
                        "page_no": chunk.page_no,
                        "section_title": chunk.section_title,
                        "metadata_json": chunk.metadata_json or {},
                        "created_at": (
                            chunk.created_at.isoformat()
                            if chunk.created_at is not None
                            else None
                        ),
                    },
                }
            )

        try:
            bulk(self.client, actions, refresh=True)
        except Exception as exc:
            raise ExternalServiceException(
                code="OPENSEARCH_BULK_UPSERT_FAILED",
                message="OpenSearch chunk 索引写入失败",
                data={
                    "url": self.url,
                    "index": self.index_name,
                    "chunk_count": len(chunks),
                    "error": str(exc),
                },
            ) from exc

    async def search(
        self,
        *,
        tenant_id: UUID,
        query: str,
        top_k: int,
        document_ids: Sequence[UUID] | None = None,
        status_filter: Sequence[str] | None = None,
    ) -> list[KeywordSearchHit]:
        if not query.strip():
            return []

        self.ensure_index()

        effective_status = list(status_filter or ["indexed", "active"])

        filters: list[dict[str, Any]] = [
            {"term": {"tenant_id": str(tenant_id)}},
            {"terms": {"document_status": effective_status}},
        ]

        if document_ids:
            filters.append(
                {
                    "terms": {
                        "document_id": [str(document_id) for document_id in document_ids]
                    }
                }
            )

        body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "content^3",
                                    "document_title^2",
                                    "section_title^2",
                                    "keywords^4",
                                ],
                                "type": "best_fields",
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
            "size": top_k,
        }

        try:
            response = self.client.search(
                index=self.index_name,
                body=body,
            )
        except NotFoundError:
            return []
        except Exception as exc:
            raise ExternalServiceException(
                code="OPENSEARCH_SEARCH_FAILED",
                message="OpenSearch 关键词检索失败",
                data={
                    "url": self.url,
                    "index": self.index_name,
                    "top_k": top_k,
                    "error": str(exc),
                },
            ) from exc

        hits: list[KeywordSearchHit] = []

        for item in response.get("hits", {}).get("hits", []):
            source = item.get("_source") or {}

            chunk_id = source.get("chunk_id")
            document_id = source.get("document_id")

            if not chunk_id or not document_id:
                continue

            hits.append(
                KeywordSearchHit(
                    chunk_id=UUID(str(chunk_id)),
                    document_id=UUID(str(document_id)),
                    score=float(item.get("_score") or 0.0),
                    payload={
                        "chunk_id": str(chunk_id),
                        "document_id": str(document_id),
                        "document_title": source.get("document_title"),
                        "document_status": source.get("document_status"),
                        "chunk_no": source.get("chunk_no"),
                        "page_no": source.get("page_no"),
                        "section_title": source.get("section_title"),
                        "content": source.get("content"),
                        "keywords_json": source.get("keywords"),
                        "metadata_json": source.get("metadata_json") or {},
                        "keyword_store": "opensearch",
                    },
                )
            )

        return hits

    @staticmethod
    def _normalize_keywords(value: Any) -> list[str]:
        if value is None:
            return []

        if isinstance(value, list):
            return [str(item) for item in value]

        if isinstance(value, dict):
            keywords = value.get("keywords")
            if isinstance(keywords, list):
                return [str(item) for item in keywords]

        return []