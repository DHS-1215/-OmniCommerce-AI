from __future__ import annotations

from app.core.exceptions import BusinessException
from app.rag.ocr.base import OCRProvider
from app.rag.ocr.mock import MockOCRProvider
from app.rag.parsers.base import DocumentParser
from app.rag.parsers.docx_parser import DocxDocumentParser
from app.rag.parsers.image_parser import ImageDocumentParser
from app.rag.parsers.pdf_parser import PdfDocumentParser
from app.rag.parsers.pptx_parser import PptxDocumentParser
from app.rag.parsers.text_parser import TextDocumentParser
from app.rag.parsers.xlsx_parser import XlsxDocumentParser

class ParserRegistry:
    """
    文档解析器注册表。

    service 层只通过 registry 获取 parser，不直接判断文件后缀。
    后续扩展 PDF / Word / Excel / PPT / OCR 时，只需要新增 parser 并注册进来。
    """

    def __init__(self) -> None:
        self._parsers: list[DocumentParser] = []

    def register(self, parser: DocumentParser) -> None:
        self._parsers.append(parser)

    def get_parser(
        self,
        *,
        filename: str,
        mime_type: str | None = None,
    ) -> DocumentParser:
        for parser in self._parsers:
            if parser.supports(filename=filename, mime_type=mime_type):
                return parser

        raise BusinessException(
            code="KNOWLEDGE_DOCUMENT_TYPE_NOT_SUPPORTED",
            message=(
                "暂不支持该文档类型。当前支持 .txt / .md / .markdown / "
                ".pdf / .docx / .xlsx / .pptx / .png / .jpg / .jpeg"
            ),
            data={
                "filename": filename,
                "mime_type": mime_type,
                "supported_extensions": [
                    ".txt",
                    ".md",
                    ".markdown",
                    ".pdf",
                    ".docx",
                    ".xlsx",
                    ".pptx",
                    ".png",
                    ".jpg",
                    ".jpeg",
                ],
            },
        )


def default_parser_registry(
    *,
    ocr_provider: OCRProvider | None = None,
) -> ParserRegistry:
    registry = ParserRegistry()
    safe_ocr_provider = ocr_provider or MockOCRProvider()

    registry.register(TextDocumentParser())
    registry.register(PdfDocumentParser(ocr_provider=safe_ocr_provider))
    registry.register(DocxDocumentParser())
    registry.register(XlsxDocumentParser())
    registry.register(PptxDocumentParser())
    registry.register(ImageDocumentParser(ocr_provider=safe_ocr_provider))

    return registry