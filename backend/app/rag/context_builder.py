from __future__ import annotations

from dataclasses import dataclass

from app.rag.retriever import RetrievalHit


@dataclass(slots=True)
class BuiltContext:
    """
    RAG 上下文组装结果。
    """

    context_text: str
    hits: list[RetrievalHit]


class RagContextBuilder:
    """
    RAG 上下文组装器。

    将检索命中的 chunk 组装为 Prompt 可用上下文。
    """

    def build(
        self,
        *,
        hits: list[RetrievalHit],
        max_chars: int = 6000,
    ) -> BuiltContext:
        parts: list[str] = []
        used_hits: list[RetrievalHit] = []
        current_length = 0

        for index, hit in enumerate(hits, start=1):
            content = str(hit.payload.get("content") or "").strip()
            if not content:
                continue

            document_title = str(hit.payload.get("document_title") or "未知文档")
            chunk_no = hit.payload.get("chunk_no")
            page_no = hit.payload.get("page_no")
            section_title = hit.payload.get("section_title")

            source_line = self._build_source_line(
                index=index,
                document_title=document_title,
                chunk_no=chunk_no,
                page_no=page_no,
                section_title=section_title,
                score=hit.score,
            )

            block = f"{source_line}\n{content}".strip()

            if current_length + len(block) > max_chars:
                break

            parts.append(block)
            used_hits.append(hit)
            current_length += len(block)

        return BuiltContext(
            context_text="\n\n---\n\n".join(parts),
            hits=used_hits,
        )

    @staticmethod
    def _build_source_line(
        *,
        index: int,
        document_title: str,
        chunk_no,
        page_no,
        section_title,
        score: float,
    ) -> str:
        source_parts = [
            f"[引用 {index}]",
            f"文档：{document_title}",
        ]

        if chunk_no is not None:
            source_parts.append(f"切片：{chunk_no}")

        if page_no is not None:
            source_parts.append(f"页码：{page_no}")

        if section_title:
            source_parts.append(f"章节：{section_title}")

        source_parts.append(f"相关度：{score:.4f}")

        return " | ".join(source_parts)