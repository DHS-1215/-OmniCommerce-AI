from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.rag.keyword_extractor import KeywordExtractor
from app.rag.parsers.base import ParsedDocument, ParsedSection
from app.rag.text_cleaner import TextCleaner


@dataclass(slots=True)
class RagChunk:
    """
    RAG 切片结果。

    注意：
    这里还不是数据库模型，只是入库前的内存结构。
    """

    chunk_no: int
    content: str
    page_no: int | None = None
    section_title: str | None = None
    keywords: list[str] = field(default_factory=list)
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class TextChunker:
    """
    RAG 文本切片器。

    按 ParsedSection 进行切片，保留页码、Sheet、Slide、parser_quality 等 metadata。
    """

    def __init__(
        self,
        *,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
        cleaner: TextCleaner | None = None,
        keyword_extractor: KeywordExtractor | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be greater than or equal to 0")

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.cleaner = cleaner or TextCleaner()
        self.keyword_extractor = keyword_extractor or KeywordExtractor()

    def chunk_document(
        self,
        *,
        document_id: UUID | None,
        parsed_document: ParsedDocument,
    ) -> list[RagChunk]:
        chunks: list[RagChunk] = []
        chunk_no = 1

        for section in parsed_document.sections:
            section_chunks = self._chunk_section(
                section=section,
                start_chunk_no=chunk_no,
                document_metadata=parsed_document.metadata,
            )
            chunks.extend(section_chunks)
            chunk_no += len(section_chunks)

        return chunks

    def _chunk_section(
        self,
        *,
        section: ParsedSection,
        start_chunk_no: int,
        document_metadata: dict[str, Any],
    ) -> list[RagChunk]:
        text_block = self.cleaner.clean(section.to_text_block())

        if not text_block:
            return []

        parts = self._split_text(text_block)

        chunks: list[RagChunk] = []
        for index, part in enumerate(parts):
            cleaned_part = self.cleaner.clean(part)

            if not cleaned_part:
                continue

            keywords = self.keyword_extractor.extract(cleaned_part)
            token_count = self.estimate_token_count(cleaned_part)

            metadata = {
                **document_metadata,
                **section.metadata,
                "chunk_index_in_section": index + 1,
                "section_title": section.title,
                "page_no": section.page_no,
                "sheet_name": section.sheet_name,
                "slide_no": section.slide_no,
            }

            chunks.append(
                RagChunk(
                    chunk_no=start_chunk_no + len(chunks),
                    content=cleaned_part,
                    page_no=section.page_no,
                    section_title=section.title,
                    keywords=keywords,
                    token_count=token_count,
                    metadata=metadata,
                )
            )

        return chunks

    def _split_text(self, text: str) -> list[str]:
        """
        优先按段落聚合，超长段落再滑窗切分。
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not paragraphs:
            return []

        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            if len(paragraph) > self.chunk_size:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._sliding_window_split(paragraph))
                continue

            candidate = paragraph if not current else f"{current}\n\n{paragraph}"

            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = paragraph

        if current:
            chunks.append(current)

        return self._apply_overlap(chunks)

    def _sliding_window_split(self, text: str) -> list[str]:
        chunks: list[str] = []
        step = self.chunk_size - self.chunk_overlap
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            part = text[start:end].strip()
            if part:
                chunks.append(part)
            if end >= len(text):
                break
            start += step

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        if self.chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        overlapped: list[str] = []

        for index, chunk in enumerate(chunks):
            if index == 0:
                overlapped.append(chunk)
                continue

            previous = chunks[index - 1]
            overlap_text = previous[-self.chunk_overlap :].strip()

            if overlap_text:
                overlapped.append(f"{overlap_text}\n\n{chunk}")
            else:
                overlapped.append(chunk)

        return overlapped

    @staticmethod
    def estimate_token_count(text: str) -> int:
        """
        粗略 token 估算。

        中文按字符近似，英文按 4 字符近似。
        这里用于元数据记录，不用于精确计费。
        """
        if not text:
            return 0

        chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        other_chars = len(text) - chinese_chars

        return chinese_chars + max(1, other_chars // 4)