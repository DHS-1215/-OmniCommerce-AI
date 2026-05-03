from __future__ import annotations

from app.rag.ocr.base import OCRProvider, OCRResult


class MockOCRProvider(OCRProvider):
    """
    测试用 OCR Provider。

    不依赖系统 Tesseract，不做真实图像识别。
    """

    def extract_text_from_image_bytes(
        self,
        *,
        image_bytes: bytes,
        language: str | None = None,
        metadata: dict | None = None,
    ) -> OCRResult:
        filename = ""
        if metadata:
            filename = str(metadata.get("filename") or metadata.get("source") or "")

        text = f"[mock_ocr] extracted text from {filename}".strip()

        return OCRResult(
            text=text,
            provider="mock",
            confidence=1.0,
            metadata={
                "language": language,
                "input_size": len(image_bytes),
                "mock": True,
                **(metadata or {}),
            },
        )