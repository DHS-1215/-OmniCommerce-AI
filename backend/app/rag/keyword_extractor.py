from __future__ import annotations

import re
from collections import Counter


class KeywordExtractor:
    """
    轻量关键词提取器。

    第一版不引入 jieba / NLP 依赖，避免依赖膨胀。
    当前策略：
    - 英文 / 数字按 token 提取
    - 中文连续文本生成 2~4 字 ngram
    - 用于 keywords_json 生成和 SimpleKeywordStore 轻量关键词检索
    """

    _ascii_token_pattern = re.compile(r"[A-Za-z0-9_\-]+")
    _chinese_text_pattern = re.compile(r"[\u4e00-\u9fff]+")

    _stopwords = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "you",
        "your",
        "are",
        "was",
        "were",
        "我们",
        "你们",
        "他们",
        "以及",
        "或者",
        "如果",
        "因为",
        "所以",
        "一个",
        "这个",
        "那个",
        "进行",
        "可以",
        "需要",
        "相关",
        "什么",
        "哪些",
        "如何",
        "是否",
    }

    def extract(self, text: str, *, max_keywords: int = 12) -> list[str]:
        if not text:
            return []

        tokens: list[str] = []

        tokens.extend(self._extract_ascii_tokens(text))
        tokens.extend(self._extract_chinese_ngrams(text))

        filtered_tokens = [
            token
            for token in tokens
            if self._is_valid_token(token)
        ]

        counter = Counter(filtered_tokens)

        return [
            token
            for token, _ in counter.most_common(max_keywords)
        ]

    def _extract_ascii_tokens(self, text: str) -> list[str]:
        return [
            token.strip().lower()
            for token in self._ascii_token_pattern.findall(text)
            if token.strip()
        ]

    def _extract_chinese_ngrams(self, text: str) -> list[str]:
        tokens: list[str] = []

        for match in self._chinese_text_pattern.findall(text):
            if len(match) < 2:
                continue

            # 保留短语本身，适合“退货”“退款”“售后”等短词。
            if 2 <= len(match) <= 8:
                tokens.append(match)

            # 生成 2~4 字 ngram，增强中文轻量匹配能力。
            for ngram_size in (2, 3, 4):
                if len(match) < ngram_size:
                    continue

                for start in range(0, len(match) - ngram_size + 1):
                    tokens.append(match[start : start + ngram_size])

        return tokens

    def _is_valid_token(self, token: str) -> bool:
        normalized = token.strip().lower()

        if not normalized:
            return False

        if normalized in self._stopwords:
            return False

        if len(normalized) < 2:
            return False

        return True