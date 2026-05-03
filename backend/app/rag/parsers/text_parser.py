from __future__ import annotations

from app.core.exceptions import BusinessException
from app.rag.parsers.base import DocumentParser, ParsedDocument, ParsedSection


class TextDocumentParser(DocumentParser):
    """
    纯文本解析器。

    支持：
    - .txt
    - .md
    - .markdown
    """

    supported_extensions = {"txt", "md", "markdown"}
    supported_mime_types = {
        "text/plain",
        "text/markdown",
        "application/octet-stream",
    }

    def parse(
        self,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        text = self._decode_text(content)

        title = filename.rsplit(".", 1)[0] if "." in filename else filename
        extension = self.get_extension(filename)

        return ParsedDocument(
            title=title,
            source_type="upload",
            mime_type=mime_type,
            sections=[
                ParsedSection(
                    title=title,
                    text=text,
                    page_no=None,
                    metadata={
                        "filename": filename,
                        "extension": extension,
                        "parser": self.__class__.__name__,
                        "parser_quality": "native_text",
                    },
                )
            ],
            metadata={
                "filename": filename,
                "extension": extension,
                "parser": self.__class__.__name__,
                "parser_quality": "native_text",
                "supported_scope": "txt/md/markdown",
            },
        )

    @staticmethod
    def _decode_text(content: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue

        raise BusinessException(
            code="KNOWLEDGE_DOCUMENT_PARSE_FAILED",
            message="文档解析失败：当前文本解析器仅支持 UTF-8 / GB18030 编码",
        )