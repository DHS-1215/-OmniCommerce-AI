from __future__ import annotations

from app.core.exceptions import BusinessException
from app.rag.ocr.base import OCRProvider
from app.rag.ocr.mock import MockOCRProvider
from app.rag.parsers.base import DocumentParser, ParsedDocument, ParsedSection


class PdfDocumentParser(DocumentParser):
    """
    PDF 解析器。

    支持：
    - 文本型 PDF：使用 PyMuPDF 直接提取文本
    - 扫描版 PDF：文本为空时，将页面渲染为图片，再走 OCRProvider

    注意：
    OCRProvider 默认使用 MockOCRProvider，测试环境不依赖真实 OCR。
    生产环境可注入 TesseractOCRProvider 或其他 OCR Provider。
    """

    supported_extensions = {"pdf"}
    supported_mime_types = {
        "application/pdf",
        "application/octet-stream",
    }

    def __init__(self, ocr_provider: OCRProvider | None = None) -> None:
        self.ocr_provider = ocr_provider or MockOCRProvider()

    def parse(
        self,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        try:
            import fitz
        except ImportError as exc:
            raise BusinessException(
                code="PDF_PARSER_DEPENDENCY_MISSING",
                message="PDF 解析依赖 PyMuPDF 未安装",
            ) from exc

        title = filename.rsplit(".", 1)[0] if "." in filename else filename
        extension = self.get_extension(filename)

        sections: list[ParsedSection] = []
        page_count = 0
        native_text_pages = 0
        ocr_pages = 0

        try:
            with fitz.open(stream=content, filetype="pdf") as pdf:
                page_count = pdf.page_count

                for page_index in range(page_count):
                    page = pdf.load_page(page_index)
                    page_no = page_index + 1

                    native_text = page.get_text("text").strip()

                    if native_text:
                        native_text_pages += 1
                        sections.append(
                            ParsedSection(
                                title=f"{title} - 第 {page_no} 页",
                                text=native_text,
                                page_no=page_no,
                                metadata={
                                    "filename": filename,
                                    "extension": extension,
                                    "parser": self.__class__.__name__,
                                    "parser_quality": "native_pdf_text",
                                    "pdf_page_no": page_no,
                                    "ocr_used": False,
                                },
                            )
                        )
                        continue

                    image_bytes = self._render_page_to_png_bytes(page)
                    ocr_result = self.ocr_provider.extract_text_from_image_bytes(
                        image_bytes=image_bytes,
                        language=None,
                        metadata={
                            "filename": filename,
                            "extension": extension,
                            "mime_type": mime_type,
                            "pdf_page_no": page_no,
                        },
                    )

                    ocr_pages += 1
                    sections.append(
                        ParsedSection(
                            title=f"{title} - 第 {page_no} 页 OCR",
                            text=ocr_result.text,
                            page_no=page_no,
                            metadata={
                                "filename": filename,
                                "extension": extension,
                                "parser": self.__class__.__name__,
                                "parser_quality": "ocr_text",
                                "pdf_page_no": page_no,
                                "ocr_used": True,
                                "ocr_provider": ocr_result.provider,
                                "ocr_confidence": ocr_result.confidence,
                                **ocr_result.metadata,
                            },
                        )
                    )
        except BusinessException:
            raise
        except Exception as exc:
            raise BusinessException(
                code="KNOWLEDGE_DOCUMENT_PARSE_FAILED",
                message="PDF 文档解析失败",
                data={
                    "filename": filename,
                    "error": str(exc),
                },
            ) from exc

        parser_quality = self._resolve_document_quality(
            native_text_pages=native_text_pages,
            ocr_pages=ocr_pages,
        )

        return ParsedDocument(
            title=title,
            source_type="upload",
            mime_type=mime_type,
            sections=sections,
            metadata={
                "filename": filename,
                "extension": extension,
                "parser": self.__class__.__name__,
                "parser_quality": parser_quality,
                "page_count": page_count,
                "native_text_pages": native_text_pages,
                "ocr_pages": ocr_pages,
                "supported_scope": "pdf/native-text/scanned-ocr",
            },
        )

    @staticmethod
    def _render_page_to_png_bytes(page) -> bytes:
        """
        将 PDF 页面渲染为 PNG 字节，供 OCR 使用。

        使用 2 倍缩放，兼顾 OCR 可读性和性能。
        """
        import fitz

        matrix = fitz.Matrix(2, 2)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return pixmap.tobytes("png")

    @staticmethod
    def _resolve_document_quality(
        *,
        native_text_pages: int,
        ocr_pages: int,
    ) -> str:
        if native_text_pages > 0 and ocr_pages == 0:
            return "native_pdf_text"
        if native_text_pages == 0 and ocr_pages > 0:
            return "ocr_pdf_text"
        if native_text_pages > 0 and ocr_pages > 0:
            return "mixed_pdf_text_ocr"
        return "empty_pdf"