from __future__ import annotations

import hashlib
import uuid
from uuid import UUID
import time

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BaseAppException, BusinessException
from app.llm.gateway import build_model_gateway
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.rag.answer_generator import RagAnswerGenerator
from app.rag.chunker import TextChunker
from app.rag.citation import CitationBuilder
from app.rag.context_builder import RagContextBuilder
from app.rag.embedder import RagEmbedder
from app.rag.keyword_store import OpenSearchKeywordStore, SimpleKeywordStore
from app.rag.parsers.registry import default_parser_registry
from app.rag.reranker import NoopReranker
from app.rag.retriever import HybridRetriever, RetrievalHit
from app.rag.vector_store import QdrantVectorStore
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.rag_retrieval_log_repository import RagRetrievalLogRepository
from app.schemas.knowledge import (
    KnowledgeAskResponse,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUploadResponse,
    KnowledgeSearchHit,
    KnowledgeSearchResponse,
)
from app.services.model_call_log_service import ModelCallLogService
from app.services.prompt_service import PromptService
from app.storage.minio_storage import MinIOStorageClient


class KnowledgeService:
    """
    企业知识库 RAG 业务服务。

    Service 负责业务编排，不直接写 SQL，不直接调用外部模型 API。
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def upload_document(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            file: UploadFile,
            title: str | None = None,
            language: str | None = "zh-CN",
            acl_json: dict | None = None,
            request_id: str | None = None,
            user_id: UUID | None = None,
    ) -> KnowledgeDocumentUploadResponse:
        """
        上传文档并完成 RAG 入库主链路。

        当前实现为同步链路：
        上传 -> 解析 -> 切片 -> embedding -> Qdrant 入库

        后续可迁移到异步任务，但主流程合同不变。
        """

        filename = file.filename or "uploaded_document"
        mime_type = file.content_type

        content = await file.read()
        if not content:
            raise BusinessException(
                code="KNOWLEDGE_DOCUMENT_EMPTY",
                message="上传文档内容为空",
                data={"filename": filename},
            )

        parser_registry = default_parser_registry()
        parser = parser_registry.get_parser(
            filename=filename,
            mime_type=mime_type,
        )
        parsed_document = parser.parse(
            filename=filename,
            content=content,
            mime_type=mime_type,
        )

        if not parsed_document.has_content():
            raise BusinessException(
                code="KNOWLEDGE_DOCUMENT_NO_TEXT",
                message="文档解析后未提取到有效文本",
                data={"filename": filename, "parser": parser.__class__.__name__},
            )

        repository = KnowledgeRepository(db)

        document_no = self._generate_document_no()
        document_title = title or parsed_document.title
        content_hash = self._sha256_hex(content)
        storage_object_key = self._build_storage_object_key(
            tenant_id=tenant_id,
            filename=filename,
        )

        storage_client = self._build_minio_storage_client()
        object_uploaded = False

        try:
            stored_object = storage_client.put_bytes(
                object_key=storage_object_key,
                content=content,
                content_type=mime_type,
            )
            object_uploaded = True
        except BaseAppException:
            raise

        document = KnowledgeDocument(
            tenant_id=tenant_id,
            document_no=document_no,
            title=document_title,
            source_type=parsed_document.source_type,
            source_uri=None,
            storage_object_key=storage_object_key,
            mime_type=mime_type,
            file_size=len(content),
            status="parsing",
            parser_status="running",
            language=language,
            acl_json=acl_json or {},
            metadata_json={
                "filename": filename,
                "content_hash": content_hash,
                "parser": parser.__class__.__name__,
                "parser_metadata": parsed_document.metadata,
                "request_id": request_id,
                "storage": {
                    "provider": "minio",
                    "bucket": stored_object.bucket,
                    "object_key": stored_object.object_key,
                    "size": stored_object.size,
                    "content_type": stored_object.content_type,
                },
            },
        )

        try:
            document = await repository.create_document(document)

            chunker = TextChunker(
                chunk_size=self.settings.rag_chunk_size,
                chunk_overlap=self.settings.rag_chunk_overlap,
            )
            rag_chunks = chunker.chunk_document(
                document_id=document.id,
                parsed_document=parsed_document,
            )

            if not rag_chunks:
                raise BusinessException(
                    code="KNOWLEDGE_DOCUMENT_CHUNK_EMPTY",
                    message="文档切片结果为空",
                    data={"document_no": document.document_no},
                )

            db_chunks: list[KnowledgeChunk] = []

            for rag_chunk in rag_chunks:
                db_chunks.append(
                    KnowledgeChunk(
                        tenant_id=tenant_id,
                        document_id=document.id,
                        chunk_no=str(rag_chunk.chunk_no),
                        title=document.title,
                        source_type=document.source_type,
                        content=rag_chunk.content,
                        content_hash=self._sha256_hex(rag_chunk.content.encode("utf-8")),
                        page_no=rag_chunk.page_no,
                        section_title=rag_chunk.section_title,
                        token_count=rag_chunk.token_count,
                        keywords_json=rag_chunk.keywords,
                        embedding_id=None,
                        vector_collection=self.settings.rag_vector_collection,
                        metadata_json={
                            **rag_chunk.metadata,
                            "document_no": document.document_no,
                            "document_title": document.title,
                        },
                    )
                )

            db_chunks = await repository.create_chunks(db_chunks)

            await repository.update_document_status(
                document_id=document.id,
                status="chunked",
                parser_status="success",
            )

            model_gateway = build_model_gateway(
                log_service=ModelCallLogService(db),
            )
            embedder = RagEmbedder(model_gateway)

            embeddings = await embedder.embed_texts(
                tenant_id=tenant_id,
                texts=[chunk.content for chunk in db_chunks],
                request_id=request_id,
                user_id=user_id,
            )

            if len(embeddings) != len(db_chunks):
                raise BusinessException(
                    code="KNOWLEDGE_EMBEDDING_COUNT_MISMATCH",
                    message="Embedding 返回数量与切片数量不一致",
                    data={
                        "chunk_count": len(db_chunks),
                        "embedding_count": len(embeddings),
                    },
                )

            vector_store = self._build_vector_store()
            points = []

            for chunk, vector in zip(db_chunks, embeddings, strict=True):
                chunk.embedding_id = str(chunk.id)
                chunk.vector_collection = self.settings.rag_vector_collection

                points.append(
                    (
                        chunk.id,
                        vector,
                        {
                            "tenant_id": str(tenant_id),
                            "document_id": str(document.id),
                            "document_no": document.document_no,
                            "document_title": document.title,
                            "chunk_id": str(chunk.id),
                            "chunk_no": chunk.chunk_no,
                            "page_no": chunk.page_no,
                            "section_title": chunk.section_title,
                            "content": chunk.content,
                            "keywords_json": chunk.keywords_json,
                            "metadata_json": chunk.metadata_json,
                        },
                    )
                )

            vector_store.upsert_chunks(points=points)

            document.status = "indexed"
            document.parser_status = "success"
            await db.flush()
            await db.refresh(document)

            keyword_store = self._build_opensearch_keyword_store()
            keyword_store.upsert_chunks(
                chunks=db_chunks,
                document=document,
            )

            await repository.update_document_status(
                document_id=document.id,
                status="indexed",
                parser_status="success",
            )

            await db.commit()
            await db.refresh(document)

        except BaseAppException:
            await db.rollback()
            if object_uploaded:
                storage_client.delete_object_safely(object_key=storage_object_key)
            raise
        except Exception as exc:
            await db.rollback()
            if object_uploaded:
                storage_client.delete_object_safely(object_key=storage_object_key)
            raise BusinessException(
                code="KNOWLEDGE_DOCUMENT_INGEST_FAILED",
                message="知识库文档入库失败",
                data={"filename": filename, "error": str(exc)},
            ) from exc

        return KnowledgeDocumentUploadResponse(
            document=KnowledgeDocumentResponse.model_validate(document),
            chunk_count=len(db_chunks),
        )

    async def list_documents(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            status_filter: str | None = None,
            keyword: str | None = None,
    ) -> KnowledgeDocumentListResponse:
        repository = KnowledgeRepository(db)

        documents, total = await repository.list_documents(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            status=status_filter,
            keyword=keyword,
        )

        return KnowledgeDocumentListResponse(
            items=[
                KnowledgeDocumentResponse.model_validate(document)
                for document in documents
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def search(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            query: str,
            top_k: int | None = None,
            request_id: str | None = None,
            user_id: UUID | None = None,
    ) -> KnowledgeSearchResponse:
        effective_top_k = top_k or self.settings.rag_top_k

        started_at = time.perf_counter()

        hits = await self._retrieve(
            db,
            tenant_id=tenant_id,
            query=query,
            top_k=effective_top_k,
            request_id=request_id,
            user_id=user_id,
        )

        retrieval_latency_ms = self._elapsed_ms(started_at)

        await self._write_retrieval_log(
            db,
            tenant_id=tenant_id,
            query=query,
            top_k=effective_top_k,
            hits=hits,
            latency_ms=retrieval_latency_ms,
            retrieval_mode="hybrid_opensearch",
            request_id=request_id,
            user_id=user_id,
            source="search",
        )

        return KnowledgeSearchResponse(
            query=query,
            items=[
                self._to_search_hit(hit)
                for hit in hits
            ],
        )

    async def ask(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            question: str,
            top_k: int | None = None,
            request_id: str | None = None,
            user_id: UUID | None = None,
    ) -> KnowledgeAskResponse:
        effective_top_k = top_k or self.settings.rag_top_k

        started_at = time.perf_counter()

        hits = await self._retrieve(
            db,
            tenant_id=tenant_id,
            query=question,
            top_k=effective_top_k,
            request_id=request_id,
            user_id=user_id,
        )

        retrieval_latency_ms = self._elapsed_ms(started_at)

        await self._write_retrieval_log(
            db,
            tenant_id=tenant_id,
            query=question,
            top_k=effective_top_k,
            hits=hits,
            latency_ms=retrieval_latency_ms,
            retrieval_mode="hybrid_opensearch",
            request_id=request_id,
            user_id=user_id,
            source="ask",
        )

        if not hits:
            return KnowledgeAskResponse(
                question=question,
                answer="知识库中没有检索到足够相关的内容，无法基于可靠来源回答该问题。",
                citations=[],
            )

        context_builder = RagContextBuilder()
        built_context = context_builder.build(hits=hits)

        citation_builder = CitationBuilder()
        citations = citation_builder.build(hits=built_context.hits)

        model_gateway = build_model_gateway(
            log_service=ModelCallLogService(db),
        )
        answer_generator = RagAnswerGenerator(
            prompt_service=PromptService(),
            model_gateway=model_gateway,
        )

        answer_result = await answer_generator.generate(
            db,
            tenant_id=tenant_id,
            question=question,
            context=built_context.context_text,
            request_id=request_id,
            user_id=user_id,
        )

        return KnowledgeAskResponse(
            question=question,
            answer=answer_result.answer,
            citations=citations,
            prompt_template_id=answer_result.prompt_template_id,
            prompt_version_id=answer_result.prompt_version_id,
        )

    async def _retrieve(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            query: str,
            top_k: int,
            request_id: str | None = None,
            user_id: UUID | None = None,
    ) -> list[RetrievalHit]:
        model_gateway = build_model_gateway(
            log_service=ModelCallLogService(db),
        )
        embedder = RagEmbedder(model_gateway)

        retriever = HybridRetriever(
            embedder=embedder,
            vector_store=self._build_vector_store(),
            keyword_store=self._build_keyword_store(db),
            vector_weight=self.settings.rag_vector_weight,
            keyword_weight=self.settings.rag_keyword_weight,
        )

        hits = await retriever.retrieve(
            tenant_id=tenant_id,
            query=query,
            top_k=top_k,
            request_id=request_id,
            user_id=user_id,
        )

        reranker = NoopReranker()
        return reranker.rerank(
            query=query,
            hits=hits,
            top_n=min(self.settings.rag_rerank_top_n, top_k),
        )

    async def _write_retrieval_log(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            query: str,
            top_k: int,
            hits: list[RetrievalHit],
            latency_ms: int,
            retrieval_mode: str,
            source: str,
            request_id: str | None = None,
            user_id: UUID | None = None,
    ) -> None:
        """
        写入 RAG 检索日志。

        这是 search / ask 的审计日志，不参与回答生成。
        """

        top_hit = hits[0] if hits else None

        scores_json = [
            {
                "chunk_id": str(hit.chunk_id),
                "document_id": str(hit.document_id),
                "vector_score": hit.vector_score,
                "keyword_score": hit.keyword_score,
                "final_score": hit.score,
            }
            for hit in hits
        ]

        repository = RagRetrievalLogRepository(db)

        try:
            await repository.create_log(
                tenant_id=tenant_id,
                user_id=user_id,
                request_id=request_id,
                query=query,
                retrieval_mode=retrieval_mode,
                top_k=top_k,
                result_count=len(hits),
                retrieved_chunk_ids=[
                    str(hit.chunk_id)
                    for hit in hits
                ],
                retrieved_document_ids=[
                    str(hit.document_id)
                    for hit in hits
                ],
                vector_score=top_hit.vector_score if top_hit else 0.0,
                keyword_score=top_hit.keyword_score if top_hit else 0.0,
                final_score=top_hit.score if top_hit else 0.0,
                scores_json=scores_json,
                latency_ms=latency_ms,
                metadata_json={
                    "source": source,
                    "retriever": "HybridRetriever",
                    "reranker": "NoopReranker",
                    "keyword_store": "OpenSearchKeywordStore",
                    "vector_store": "QdrantVectorStore",
                },
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)

    def _build_vector_store(self) -> QdrantVectorStore:
        return QdrantVectorStore(
            url=self.settings.qdrant_url,
            collection_name=self.settings.rag_vector_collection,
            vector_size=self.settings.rag_vector_size,
        )

    def _build_minio_storage_client(self) -> MinIOStorageClient:
        return MinIOStorageClient(
            endpoint=self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            bucket_name=self.settings.minio_bucket_knowledge,
            secure=self.settings.minio_secure,
        )

    def _build_keyword_store(self, db: AsyncSession):
        """
        构建关键词检索实现。

        6B 默认使用 OpenSearchKeywordStore。
        如果 OpenSearch 不可用，可临时回退 SimpleKeywordStore。
        """

        if self.settings.opensearch_url:
            return self._build_opensearch_keyword_store()

        return SimpleKeywordStore(db_session=db)

    def _build_opensearch_keyword_store(self) -> OpenSearchKeywordStore:
        return OpenSearchKeywordStore(
            url=self.settings.opensearch_url,
            index_name=self.settings.opensearch_index,
            username=self.settings.opensearch_username,
            password=self.settings.opensearch_password,
        )

    @staticmethod
    def _to_search_hit(hit: RetrievalHit) -> KnowledgeSearchHit:
        return KnowledgeSearchHit(
            document_id=hit.document_id,
            document_title=str(hit.payload.get("document_title") or "未知文档"),
            chunk_id=hit.chunk_id,
            chunk_no=str(hit.payload.get("chunk_no") or ""),
            page_no=hit.payload.get("page_no"),
            section_title=hit.payload.get("section_title"),
            score=hit.score,
            vector_score=hit.vector_score,
            keyword_score=hit.keyword_score,
            content_snippet=KnowledgeService._build_snippet(
                str(hit.payload.get("content") or "")
            ),
            metadata_json=hit.payload.get("metadata_json"),
        )

    @staticmethod
    def _generate_document_no() -> str:
        return f"KD{uuid.uuid4().hex[:16].upper()}"

    @staticmethod
    def _sha256_hex(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _build_storage_object_key(
            *,
            tenant_id: UUID,
            filename: str,
    ) -> str:
        safe_filename = filename.replace("\\", "_").replace("/", "_")
        return f"knowledge/{tenant_id}/{uuid.uuid4().hex}_{safe_filename}"

    @staticmethod
    def _build_snippet(content: str, *, max_chars: int = 180) -> str:
        cleaned = " ".join(content.split())

        if len(cleaned) <= max_chars:
            return cleaned

        return cleaned[:max_chars].rstrip() + "..."
