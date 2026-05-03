from __future__ import annotations

from app.rag.ocr.base import OCRProvider
from app.rag.ocr.mock import MockOCRProvider
from app.rag.parsers.base import DocumentParser, ParsedDocument, ParsedSection


class ImageDocumentParser(DocumentParser):
    """
    图片 OCR 解析器。

    支持：
    - .png
    - .jpg
    - .jpeg

    默认使用 MockOCRProvider，避免测试环境依赖真实 OCR。
    生产环境可在 registry 中注入 TesseractOCRProvider 或其他 OCR Provider。
    """

    supported_extensions = {"png", "jpg", "jpeg"}
    supported_mime_types = {
        "image/png",
        "image/jpeg",
        "image/jpg",
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
        title = filename.rsplit(".", 1)[0] if "." in filename else filename
        extension = self.get_extension(filename)

        ocr_result = self.ocr_provider.extract_text_from_image_bytes(
            image_bytes=content,
            language=None,
            metadata={
                "filename": filename,
                "extension": extension,
                "mime_type": mime_type,
            },
        )

        return ParsedDocument(
            title=title,
            source_type="upload",
            mime_type=mime_type,
            sections=[
                ParsedSection(
                    title=title,
                    text=ocr_result.text,
                    page_no=1,
                    metadata={
                        "filename": filename,
                        "extension": extension,
                        "parser": self.__class__.__name__,
                        "parser_quality": "ocr_text",
                        "ocr_provider": ocr_result.provider,
                        "ocr_confidence": ocr_result.confidence,
                        **ocr_result.metadata,
                    },
                )
            ],
            metadata={
                "filename": filename,
                "extension": extension,
                "parser": self.__class__.__name__,
                "parser_quality": "ocr_text",
                "ocr_provider": ocr_result.provider,
                "ocr_confidence": ocr_result.confidence,
                "supported_scope": "png/jpg/jpeg",
            },
        )