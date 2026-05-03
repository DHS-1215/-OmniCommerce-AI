# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 21:57
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class OCRResult:
    """
    OCR 识别结果。
    """

    text: str
    provider: str
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OCRProvider(ABC):
    """
    OCR Provider 抽象。

    Parser 依赖 OCRProvider 抽象，不直接依赖 pytesseract。
    测试环境可注入 MockOCRProvider，避免 pytest 依赖真实 OCR 引擎。
    """

    @abstractmethod
    def extract_text_from_image_bytes(
            self,
            *,
            image_bytes: bytes,
            language: str | None = None,
            metadata: dict[str, Any] | None = None,
    ) -> OCRResult:
        """
        从图片字节中识别文本。
        """
