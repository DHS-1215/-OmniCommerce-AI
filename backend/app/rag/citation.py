from __future__ import annotations

from uuid import UUID

from app.rag.retriever import RetrievalHit
from app.schemas.knowledge import KnowledgeCitation


class CitationBuilder:
    """
    引用来源构造器。

    RAG 回答必须返回引用来源，尤其企业政策类回答不能无来源生成。
    """

    def build(self, *, hits: list[RetrievalHit]) -> list[KnowledgeCitation]:
        citations: list[KnowledgeCitation] = []

        seen_chunk_ids: set[UUID] = set()

        for hit in hits:
            if hit.chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(hit.chunk_id)

            content = str(hit.payload.get("content") or "")
            snippet = self._build_snippet(content)

            citations.append(
                KnowledgeCitation(
                    document_id=hit.document_id,
                    document_title=str(hit.payload.get("document_title") or "未知文档"),
                    chunk_id=hit.chunk_id,
                    chunk_no=str(hit.payload.get("chunk_no") or 0),
                    page_no=hit.payload.get("page_no"),
                    section_title=hit.payload.get("section_title"),
                    score=hit.score,
                    content_snippet=snippet,
                )
            )

        return citations

    @staticmethod
    def _build_snippet(content: str, *, max_chars: int = 180) -> str:
        cleaned = " ".join(content.split())

        if len(cleaned) <= max_chars:
            return cleaned

        return cleaned[:max_chars].rstrip() + "..."