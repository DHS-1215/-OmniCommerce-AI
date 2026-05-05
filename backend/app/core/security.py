# -*- coding: utf-8 -*-
from __future__ import annotations

"""
认证安全工具。

窗口 13 设计目标：
- 不引入额外 JWT / 密码库依赖，降低 Docker build 和测试环境不确定性；
- 使用标准库实现 HS256 JWT 签发与解析；
- 使用 PBKDF2-HMAC-SHA256 存储密码 hash，不保存明文密码。
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import timedelta
from typing import Any

from app.core.config import get_settings

_PASSWORD_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 260_000


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def hash_password(password: str) -> str:
    """
    生成密码 hash。

    格式：
    pbkdf2_sha256$iterations$salt$hash
    """

    if not password:
        raise ValueError("password must not be empty")

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PASSWORD_ITERATIONS,
    ).hex()

    return f"{_PASSWORD_ALGORITHM}${_PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    校验密码。

    任何格式异常都返回 False，避免把 hash 解析细节暴露给调用方。
    """

    try:
        algorithm, iterations_raw, salt, expected_digest = password_hash.split("$", 3)
        if algorithm != _PASSWORD_ALGORITHM:
            return False

        iterations = int(iterations_raw)
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()

        return hmac.compare_digest(actual_digest, expected_digest)
    except Exception:
        return False


def create_access_token(
        claims: dict[str, Any],
        expires_delta: timedelta | None = None,
) -> str:
    """
    签发 HS256 JWT。

    claims 至少应包含：
    - sub
    - user_no
    - tenant_id
    - role

    exp 如果调用方未传，则按 settings.jwt_expire_minutes 自动补充。
    """

    settings = get_settings()

    if settings.jwt_algorithm != "HS256":
        raise ValueError("Only HS256 is supported by the built-in JWT implementation")

    now = int(time.time())
    expire_seconds = (
        int(expires_delta.total_seconds())
        if expires_delta is not None
        else settings.jwt_expire_minutes * 60
    )

    payload = dict(claims)
    payload.setdefault("iat", now)
    payload.setdefault("exp", now + expire_seconds)

    header = {
        "alg": settings.jwt_algorithm,
        "typ": "JWT",
    }

    header_segment = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_segment = _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    return f"{header_segment}.{payload_segment}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    """
    解析并校验 HS256 JWT。

    校验内容：
    - token 结构
    - alg 是否为 HS256
    - 签名是否匹配
    - exp 是否过期

    失败时抛出 ValueError，由上层依赖转换为统一 UnauthorizedException。
    """

    settings = get_settings()

    try:
        header_segment, payload_segment, signature_segment = token.split(".", 2)
    except ValueError as exc:
        raise ValueError("Invalid token format") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    actual_signature = _base64url_decode(signature_segment)

    if not hmac.compare_digest(actual_signature, expected_signature):
        raise ValueError("Invalid token signature")

    try:
        header = json.loads(_base64url_decode(header_segment))
        payload = json.loads(_base64url_decode(payload_segment))
    except Exception as exc:
        raise ValueError("Invalid token payload") from exc

    if header.get("alg") != "HS256":
        raise ValueError("Unsupported token algorithm")

    exp = payload.get("exp")
    if exp is None:
        raise ValueError("Token missing exp")

    if int(exp) < int(time.time()):
        raise ValueError("Token expired")

    return payload
