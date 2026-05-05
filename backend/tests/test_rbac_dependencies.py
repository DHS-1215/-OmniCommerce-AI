# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
from uuid import UUID

import pytest

from app.core.auth_dependencies import (
    CurrentUser,
    ensure_tenant_allowed,
    require_roles,
)
from app.core.config import get_settings
from app.core.exceptions import ForbiddenException


TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000002")


def _admin_user() -> CurrentUser:
    return CurrentUser(
        account_id=UUID("20000000-0000-0000-0000-000000000001"),
        user_id=UUID("10000000-0000-0000-0000-000000000001"),
        user_no="U100001",
        username="admin",
        tenant_id=TENANT_ID,
        role="admin",
    )


def _viewer_user() -> CurrentUser:
    return CurrentUser(
        account_id=UUID("20000000-0000-0000-0000-000000000003"),
        user_id=UUID("11000000-0000-0000-0000-000000000001"),
        user_no="U200001",
        username="viewer",
        tenant_id=TENANT_ID,
        role="viewer",
    )


def test_require_roles_should_noop_when_auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()

    dependency = require_roles("admin")
    result = asyncio.run(dependency(current_user=None))

    assert result is None

    get_settings.cache_clear()


def test_require_roles_should_allow_admin_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    get_settings.cache_clear()

    dependency = require_roles("admin")
    result = asyncio.run(dependency(current_user=_admin_user()))

    assert result.role == "admin"

    get_settings.cache_clear()


def test_require_roles_should_reject_viewer_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    get_settings.cache_clear()

    dependency = require_roles("admin")

    with pytest.raises(ForbiddenException):
        asyncio.run(dependency(current_user=_viewer_user()))

    get_settings.cache_clear()


def test_ensure_tenant_allowed_should_return_request_tenant_when_auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()

    tenant_id = ensure_tenant_allowed(
        provided_tenant_id=TENANT_ID,
        current_user=None,
    )

    assert tenant_id == TENANT_ID

    get_settings.cache_clear()


def test_ensure_tenant_allowed_should_return_token_tenant_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    get_settings.cache_clear()

    tenant_id = ensure_tenant_allowed(
        provided_tenant_id=TENANT_ID,
        current_user=_admin_user(),
    )

    assert tenant_id == TENANT_ID

    get_settings.cache_clear()


def test_ensure_tenant_allowed_should_reject_mismatch_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    get_settings.cache_clear()

    with pytest.raises(ForbiddenException):
        ensure_tenant_allowed(
            provided_tenant_id=OTHER_TENANT_ID,
            current_user=_admin_user(),
        )

    get_settings.cache_clear()