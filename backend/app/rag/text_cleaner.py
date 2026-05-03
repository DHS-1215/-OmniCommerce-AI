from __future__ import annotations

import re


class TextCleaner:
    """
    RAG 文本清洗器。

    只做保守清洗，不做激进改写，避免破坏企业文档原意。
    """

    _multi_blank_line_pattern = re.compile(r"\n{3,}")
    _horizontal_space_pattern = re.compile(r"[ \t\u3000]+")

    def clean(self, text: str) -> str:
        if not text:
            return ""

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized = self._strip_line_spaces(normalized)
        normalized = self._collapse_horizontal_spaces(normalized)
        normalized = self._collapse_blank_lines(normalized)

        return normalized.strip()

    def _strip_line_spaces(self, text: str) -> str:
        return "\n".join(line.strip() for line in text.split("\n"))

    def _collapse_horizontal_spaces(self, text: str) -> str:
        cleaned_lines = []
        for line in text.split("\n"):
            cleaned_lines.append(self._horizontal_space_pattern.sub(" ", line))
        return "\n".join(cleaned_lines)

    def _collapse_blank_lines(self, text: str) -> str:
        return self._multi_blank_line_pattern.sub("\n\n", text)