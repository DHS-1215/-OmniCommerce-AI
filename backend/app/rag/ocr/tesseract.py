from __future__ import annotations

from io import BytesIO

from PIL import Image
import pytesseract

from app.core.exceptions import BusinessException
from app.rag.ocr.base import OCRProvider, OCRResult


class TesseractOCRProvider(OCRProvider):
    """
    Tesseract OCR Provider。

    注意：
    pytesseract 只是 Python 封装，运行环境还需要安装 Tesseract OCR 引擎。
    测试环境默认不要依赖这个 Provider。
    """

    def extract_text_from_image_bytes(
        self,
        *,
        image_bytes: bytes,
        language: str | None = None,
        metadata: dict | None = None,
    ) -> OCRResult:
        try:
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(
                image,
                lang=language or "eng+chi_sim",
            )
        except Exception as exc:
            raise BusinessException(
                code="OCR_EXTRACT_FAILED",
                message="OCR 文本识别失败",
                data={
                    "provider": "tesseract",
                    "error": str(exc),
                    **(metadata or {}),
                },
            ) from exc

        return OCRResult(
            text=text.strip(),
            provider="tesseract",
            confidence=None,
            metadata={
                "language": language or "eng+chi_sim",
                "parser_quality": "ocr_text",
                **(metadata or {}),
            },
        )