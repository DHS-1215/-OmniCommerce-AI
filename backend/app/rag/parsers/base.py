from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ParsedTable:
    """
    解析得到的表格结构。

    rows 使用二维数组表达，后续可以统一转 Markdown 表格或结构化文本。
    对复杂表格、跨页表格、扫描表格等情况，可以通过 metadata.parser_quality 标记降级质量。
    """

    rows: list[list[str]]
    caption: str | None = None
    page_no: int | None = None
    sheet_name: str | None = None
    slide_no: int | None = None
    row_start: int | None = None
    row_end: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """
        将基础表格转换为 Markdown 表格。

        如果表格为空，返回空字符串。
        如果只有一行，把这一行视为表头，同时补一个空数据行，避免 Markdown 表格不成形。
        """
        if not self.rows:
            return ""

        normalized_rows = [
            [self._normalize_cell(cell) for cell in row]
            for row in self.rows
            if row
        ]

        if not normalized_rows:
            return ""

        max_cols = max(len(row) for row in normalized_rows)
        padded_rows = [
            row + [""] * (max_cols - len(row))
            for row in normalized_rows
        ]

        header = padded_rows[0]
        body = padded_rows[1:] if len(padded_rows) > 1 else [[""] * max_cols]

        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * max_cols) + " |",
        ]

        for row in body:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    @staticmethod
    def _normalize_cell(value: Any) -> str:
        text = "" if value is None else str(value)
        return text.replace("\n", " ").replace("|", "\\|").strip()


@dataclass(slots=True)
class ParsedSection:
    """
    文档解析后的基础内容单元。

    section 是切片前的结构化文本单位。
    例如：
    - PDF 的某一页
    - DOCX 的一组段落
    - XLSX 的某个 Sheet
    - PPTX 的某一页 Slide
    - 图片 OCR 的文本
    """

    title: str | None
    text: str
    page_no: int | None = None
    sheet_name: str | None = None
    slide_no: int | None = None
    tables: list[ParsedTable] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_text_block(self) -> str:
        """
        将 section 转成可进入清洗、切片、Embedding 的文本块。
        """
        parts: list[str] = []

        if self.title:
            parts.append(f"# {self.title}")

        if self.text.strip():
            parts.append(self.text.strip())

        for table in self.tables:
            table_markdown = table.to_markdown()
            if table.caption:
                parts.append(f"表格：{table.caption}")
            if table_markdown:
                parts.append(table_markdown)

        return "\n\n".join(part for part in parts if part.strip())


@dataclass(slots=True)
class ParsedDocument:
    """
    文档解析结果统一协议。

    所有 Parser 都必须输出这个结构，不允许各自返回随意 dict。
    """

    title: str
    source_type: str
    sections: list[ParsedSection]
    mime_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content(self) -> str:
        """
        兼容下游清洗 / 切片使用的全文文本。
        """
        return "\n\n".join(
            section.to_text_block()
            for section in self.sections
            if section.to_text_block().strip()
        )

    def has_content(self) -> bool:
        return bool(self.content.strip())


class DocumentParser(ABC):
    """
    文档解析器抽象基类。

    Parser 只负责：
    文件字节 -> ParsedDocument

    Parser 不负责：
    - 文档元数据入库
    - Chunk 切片
    - Embedding
    - Qdrant 入库
    - RAG 检索
    - 回答生成
    """

    supported_extensions: set[str] = set()
    supported_mime_types: set[str] = set()

    def supports(self, *, filename: str, mime_type: str | None = None) -> bool:
        extension = self.get_extension(filename)

        if extension in self.supported_extensions:
            return True

        if mime_type and mime_type in self.supported_mime_types:
            return True

        return False

    @abstractmethod
    def parse(
        self,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        """
        解析上传文件内容。
        """

    @staticmethod
    def get_extension(filename: str) -> str:
        if "." not in filename:
            return ""
        return filename.rsplit(".", 1)[-1].lower()