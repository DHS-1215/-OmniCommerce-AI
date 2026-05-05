# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_should_verify_successfully():
    password_hash = hash_password("demo-password")

    assert password_hash != "demo-password"
    assert verify_password("demo-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_decode_access_token_should_return_claims():
    token = create_access_token(
        {
            "sub": "10000000-0000-0000-0000-000000000001",
            "user_id": "10000000-0000-0000-0000-000000000001",
            "user_no": "U100001",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "role": "admin",
            "account_id": "20000000-0000-0000-0000-000000000001",
        }
    )

    claims = decode_access_token(token)

    assert claims["sub"] == "10000000-0000-0000-0000-000000000001"
    assert claims["user_no"] == "U100001"
    assert claims["tenant_id"] == "00000000-0000-0000-0000-000000000001"
    assert claims["role"] == "admin"
    assert "exp" in claims


def test_decode_access_token_should_reject_expired_token():
    token = create_access_token(
        {
            "sub": "10000000-0000-0000-0000-000000000001",
            "user_id": "10000000-0000-0000-0000-000000000001",
            "user_no": "U100001",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "role": "admin",
            "account_id": "20000000-0000-0000-0000-000000000001",
        },
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(ValueError):
        decode_access_token(token)
