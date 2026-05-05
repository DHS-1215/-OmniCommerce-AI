from __future__ import annotations

from app.services.sql_guard_service import SqlGuardService


def test_guard_allows_safe_select_with_tenant_filter() -> None:
    guard = SqlGuardService()

    result = guard.guard(
        """
        SELECT order_no, paid_amount
        FROM order_info
        WHERE tenant_id = :tenant_id
          AND deleted_at IS NULL
        """
    )

    assert result.passed is True
    assert result.readonly is True
    assert result.tables == ["order_info"]


def test_guard_rejects_delete() -> None:
    guard = SqlGuardService()

    result = guard.guard(
        "DELETE FROM order_info WHERE tenant_id = :tenant_id"
    )

    assert result.passed is False
    assert result.error_code == "SQL_ONLY_SELECT_ALLOWED"


def test_guard_rejects_dangerous_keyword_inside_select() -> None:
    guard = SqlGuardService()

    result = guard.guard(
        "SELECT order_no FROM order_info WHERE tenant_id = :tenant_id; DROP TABLE product;"
    )

    assert result.passed is False
    assert result.error_code == "SQL_MULTIPLE_STATEMENTS_FORBIDDEN"


def test_guard_rejects_multiple_statements() -> None:
    guard = SqlGuardService()

    result = guard.guard(
        "SELECT order_no FROM order_info WHERE tenant_id = :tenant_id; SELECT product_no FROM product;"
    )

    assert result.passed is False
    assert result.error_code == "SQL_MULTIPLE_STATEMENTS_FORBIDDEN"


def test_guard_rejects_table_not_in_whitelist() -> None:
    guard = SqlGuardService()

    result = guard.guard(
        """
        SELECT id, usename
        FROM pg_user
        WHERE tenant_id = :tenant_id
        """
    )

    assert result.passed is False
    assert result.error_code == "SQL_TABLE_NOT_ALLOWED"


def test_guard_rejects_missing_tenant_filter() -> None:
    guard = SqlGuardService()

    result = guard.guard(
        """
        SELECT order_no, paid_amount
        FROM order_info
        WHERE deleted_at IS NULL
        """
    )

    assert result.passed is False
    assert result.error_code == "SQL_TENANT_FILTER_REQUIRED"


def test_guard_rejects_select_star() -> None:
    guard = SqlGuardService()

    result = guard.guard(
        "SELECT * FROM order_info WHERE tenant_id = :tenant_id"
    )

    assert result.passed is False
    assert result.error_code == "SQL_SELECT_STAR_FORBIDDEN"


def test_guard_allows_count_star() -> None:
    guard = SqlGuardService()

    result = guard.guard(
        "SELECT COUNT(*) AS order_count FROM order_info WHERE tenant_id = :tenant_id"
    )

    assert result.passed is True
    assert result.tables == ["order_info"]


def test_guard_allows_join_on_whitelisted_tables() -> None:
    guard = SqlGuardService()

    result = guard.guard(
        """
        SELECT oi.order_no, p.product_no
        FROM order_item oi
        JOIN product p ON p.id = oi.product_id
        WHERE oi.tenant_id = :tenant_id
          AND p.tenant_id = :tenant_id
        """
    )

    assert result.passed is True
    assert result.tables == ["order_item", "product"]