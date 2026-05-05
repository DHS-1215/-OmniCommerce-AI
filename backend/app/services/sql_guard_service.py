# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 22:34
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import re

from app.schemas.operation_copilot import SqlGuardResult


class SqlGuardService:
    """SQL 只读安全检查服务。

    最高优先级规则：
    1. SQL 必须先 guard，再执行；
    2. 只允许 SELECT / WITH ... SELECT；
    3. 禁止写操作、多语句、非白名单表、无 tenant_id、SELECT *。
    """

    FORBIDDEN_KEYWORDS = {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "grant",
        "revoke",
        "copy",
        "call",
        "exec",
        "execute",
        "merge",
        "vacuum",
        "analyze",
    }

    DEFAULT_ALLOWED_TABLES = {
        "order_info",
        "order_item",
        "product",
        "product_sku",
        "product_review",
        "user_profile",
        "after_sale_ticket",
        "customer_service_ticket",
    }

    def __init__(self, allowed_tables: set[str] | None = None) -> None:
        self.allowed_tables = allowed_tables or self.DEFAULT_ALLOWED_TABLES

    def guard(self, sql: str) -> SqlGuardResult:
        normalized = self.normalize(sql)
        if not normalized:
            return self._reject("SQL_EMPTY", "SQL 不能为空。")

        if self._has_multiple_statements(normalized):
            return self._reject("SQL_MULTIPLE_STATEMENTS_FORBIDDEN", "禁止执行多语句 SQL。")

        normalized = normalized.rstrip(";").strip()
        lowered_for_keywords = self._strip_string_literals(normalized).lower()

        if not self._is_readonly_query(lowered_for_keywords):
            return self._reject("SQL_ONLY_SELECT_ALLOWED", "只允许 SELECT 或 WITH ... SELECT 查询。")

        forbidden = self._find_forbidden_keyword(lowered_for_keywords)
        if forbidden:
            return self._reject("SQL_DANGEROUS_KEYWORD", f"SQL 包含危险关键字：{forbidden}")

        if self._has_select_star(lowered_for_keywords):
            return self._reject("SQL_SELECT_STAR_FORBIDDEN", "禁止使用 SELECT *，必须显式选择字段。")

        if "tenant_id" not in lowered_for_keywords:
            return self._reject("SQL_TENANT_FILTER_REQUIRED", "SQL 必须包含 tenant_id 租户过滤条件。")

        tables = self.extract_tables(normalized)
        if not tables:
            return self._reject("SQL_TABLE_REQUIRED", "未识别到查询表。")

        illegal_tables = [
            table for table in tables
            if table not in self.allowed_tables
        ]
        if illegal_tables:
            return self._reject(
                "SQL_TABLE_NOT_ALLOWED",
                f"SQL 访问了非白名单表：{', '.join(sorted(illegal_tables))}",
                tables=tables,
            )

        return SqlGuardResult(
            passed=True,
            readonly=True,
            normalized_sql=normalized,
            tables=sorted(tables),
        )

    def normalize(self, sql: str) -> str:
        value = sql or ""
        value = re.sub(r"/\*.*?\*/", " ", value, flags=re.DOTALL)
        value = re.sub(r"--.*?$", " ", value, flags=re.MULTILINE)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def extract_tables(self, sql: str) -> list[str]:
        lowered = sql.lower()
        cte_names = set(re.findall(r"(?:with|,)\s+([a-zA-Z_][\w]*)\s+as\s*\(", lowered))

        tables: set[str] = set()
        for match in re.finditer(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)(?:\s+|$)", lowered):
            raw_table = match.group(1).strip()
            table = raw_table.split(".")[-1]
            if table in cte_names:
                continue
            if table.startswith("pg_") or table in {"information_schema"}:
                tables.add(table)
                continue
            tables.add(table)

        return sorted(tables)

    def _is_readonly_query(self, lowered_sql: str) -> bool:
        stripped = lowered_sql.strip()
        if stripped.startswith("select "):
            return True
        if stripped.startswith("with "):
            return bool(re.search(r"\)\s*select\s+", stripped))
        return False

    def _find_forbidden_keyword(self, lowered_sql: str) -> str | None:
        for keyword in sorted(self.FORBIDDEN_KEYWORDS):
            if re.search(rf"\b{keyword}\b", lowered_sql):
                return keyword.upper()
        return None

    def _has_multiple_statements(self, sql: str) -> bool:
        stripped = sql.strip()
        if ";" not in stripped:
            return False
        if stripped.endswith(";") and stripped.count(";") == 1:
            return False
        return True

    def _has_select_star(self, lowered_sql: str) -> bool:
        if re.search(r"\bselect\s+(?:distinct\s+)?\*", lowered_sql):
            return True
        if re.search(r"\bselect\b[^;]*\b[a-zA-Z_][\w]*\.\*", lowered_sql):
            return True
        return False

    def _strip_string_literals(self, sql: str) -> str:
        return re.sub(r"'(?:''|[^'])*'", "''", sql)

    def _reject(
            self,
            error_code: str,
            reason: str,
            tables: list[str] | None = None,
    ) -> SqlGuardResult:
        return SqlGuardResult(
            passed=False,
            readonly=False,
            tables=tables or [],
            rejected_reason=reason,
            error_code=error_code,
        )
