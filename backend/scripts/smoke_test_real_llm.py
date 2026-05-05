from __future__ import annotations

import json
import os
from typing import Any

import httpx


BASE_URL = os.getenv("API_BASE_URL", os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:8002")).rstrip("/")
TENANT_ID = os.getenv("TENANT_ID", "00000000-0000-0000-0000-000000000001")

EXPECTED_PROVIDER = os.getenv("REAL_LLM_PROVIDER", os.getenv("DEFAULT_LLM_PROVIDER", "openai_compatible"))
EXPECTED_MODEL = os.getenv("REAL_LLM_MODEL", os.getenv("DEFAULT_LLM_MODEL", "qwen-turbo"))

MOCK_PREFIX = "[mock]"
MOCK_FAILURE_HINT = (
    "业务链路仍在使用 mock provider，请检查 backend 容器 "
    "DEFAULT_LLM_PROVIDER / DEFAULT_LLM_MODEL 环境变量，"
    "以及 Prompt 版本 model_config_json 是否仍配置为 mock。"
)


def print_section(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def compact(value: Any, max_len: int = 1400) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2)
    if len(text) > max_len:
        return text[:max_len] + "\n...<truncated>"
    return text


def post_json(client: httpx.Client, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"{BASE_URL}{path}", json=payload)
    print(f"POST {path} -> HTTP {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(response.text[:1000])
        raise

    print(compact(data))
    return data


def get_json(client: httpx.Client, path: str) -> dict[str, Any]:
    response = client.get(f"{BASE_URL}{path}")
    print(f"GET {path} -> HTTP {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(response.text[:1000])
        raise

    print(compact(data))
    return data


def nested_get(data: dict[str, Any], path: list[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def is_success(data: dict[str, Any]) -> bool:
    return data.get("success") is True


def text_starts_with_mock(value: Any) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        value = str(value)
    return value.lstrip().startswith(MOCK_PREFIX)


def check_success(name: str, data: dict[str, Any], failures: list[str]) -> bool:
    if is_success(data):
        print(f"[OK] {name}: success=true")
        return True

    print(f"[FAIL] {name}: success is not true")
    failures.append(f"{name}: success is not true")
    return False


def check_no_mock_prefix(
    name: str,
    data: dict[str, Any],
    paths: list[list[str]],
    failures: list[str],
) -> None:
    checked_any = False

    for path in paths:
        value = nested_get(data, path)
        if value is None:
            continue

        checked_any = True
        path_text = ".".join(path)

        if text_starts_with_mock(value):
            print(f"[FAIL] {name}: {path_text} starts with {MOCK_PREFIX}")
            print(MOCK_FAILURE_HINT)
            failures.append(f"{name}: {path_text} starts with {MOCK_PREFIX}")
        else:
            print(f"[OK] {name}: {path_text} does not start with {MOCK_PREFIX}")

    if not checked_any:
        print(f"[WARN] {name}: no configured text field was found for mock-prefix check")
        failures.append(f"{name}: no configured text field was found for mock-prefix check")


def check_direct_model_gateway(data: dict[str, Any], failures: list[str]) -> None:
    if not check_success("direct_llm_chat", data, failures):
        return

    provider = nested_get(data, ["data", "provider"])
    model_name = nested_get(data, ["data", "model_name"])
    content = nested_get(data, ["data", "content"])

    if provider != EXPECTED_PROVIDER:
        print(f"[FAIL] direct_llm_chat: provider={provider!r}, expected={EXPECTED_PROVIDER!r}")
        failures.append(f"direct_llm_chat: provider mismatch, got {provider!r}")
    else:
        print(f"[OK] direct_llm_chat: provider={provider}")

    if model_name != EXPECTED_MODEL:
        print(f"[FAIL] direct_llm_chat: model_name={model_name!r}, expected={EXPECTED_MODEL!r}")
        failures.append(f"direct_llm_chat: model mismatch, got {model_name!r}")
    else:
        print(f"[OK] direct_llm_chat: model_name={model_name}")

    if text_starts_with_mock(content):
        print(f"[FAIL] direct_llm_chat: content starts with {MOCK_PREFIX}")
        print(MOCK_FAILURE_HINT)
        failures.append("direct_llm_chat: content starts with [mock]")
    else:
        print("[OK] direct_llm_chat: content does not start with [mock]")


def main() -> int:
    print_section("Real LLM Smoke Test")
    print(f"BASE_URL={BASE_URL}")
    print(f"TENANT_ID={TENANT_ID}")
    print(f"EXPECTED_PROVIDER={EXPECTED_PROVIDER}")
    print(f"EXPECTED_MODEL={EXPECTED_MODEL}")
    print("LLM_API_KEY is never printed by this script.")
    print()
    print("Before running this script, verify backend container environment:")
    print(
        "docker compose exec backend sh -lc "
        "\"env | grep -E 'DEFAULT_LLM|LLM_BASE_URL|LLM_API_KEY|REAL_LLM' "
        "| sed -E 's#^(LLM_API_KEY=).*#\\1***MASKED***#'\""
    )

    failures: list[str] = []

    with httpx.Client(timeout=120.0, trust_env=False) as client:
        print_section("1. Health Check")
        health = get_json(client, "/api/v1/health")
        check_success("health", health, failures)

        print_section("2. Direct ModelGateway Chat")
        llm_chat = post_json(
            client,
            "/api/v1/llm/chat",
            {
                "tenant_id": TENANT_ID,
                "provider": EXPECTED_PROVIDER,
                "model": EXPECTED_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": "请用一句话说明你已接入真实模型链路。",
                    }
                ],
            },
        )
        check_direct_model_gateway(llm_chat, failures)

        print_section("3. RAG Ask Must Not Return [mock]")
        rag = post_json(
            client,
            "/api/v1/knowledge/ask",
            {
                "tenant_id": TENANT_ID,
                "question": "七天无理由退货有哪些条件？",
                "top_k": 5,
            },
        )
        if check_success("rag_ask", rag, failures):
            check_no_mock_prefix(
                "rag_ask",
                rag,
                [["data", "answer"]],
                failures,
            )

        print_section("4. Customer Service Policy Query Must Not Return [mock]")
        cs_policy = post_json(
            client,
            "/api/v1/agents/customer-service/chat",
            {
                "tenant_id": TENANT_ID,
                "session_id": "smoke_cs_policy_real_llm",
                "user_no": "U100001",
                "message": "七天无理由退货政策是什么？",
                "conversation_summary": "",
                "context": {},
            },
        )
        if check_success("customer_service_policy", cs_policy, failures):
            check_no_mock_prefix(
                "customer_service_policy",
                cs_policy,
                [["data", "answer"]],
                failures,
            )

        print_section("5. Content Generation Must Not Return [mock]")
        content = post_json(
            client,
            "/api/v1/content/generate/product-title",
            {
                "tenant_id": TENANT_ID,
                "product_no": "P100001",
                "requirements": "突出办公室使用、安全、省心、智能控温",
                "tone": "专业可信",
            },
        )
        if check_success("content_generation_product_title", content, failures):
            check_no_mock_prefix(
                "content_generation_product_title",
                content,
                [
                    ["data", "asset", "content"],
                    ["data", "content"],
                ],
                failures,
            )

    print_section("Smoke Test Summary")

    if failures:
        print("Real LLM smoke test FAILED.")
        print()
        print("Failure details:")
        for item in failures:
            print(f"- {item}")

        print()
        print(MOCK_FAILURE_HINT)
        print()
        print("This script is intentionally not part of default pytest.")
        print("Default automated tests should continue to use mock provider.")
        print("A failure here means the real-model/demo path needs checking, not that the mock test suite failed.")
        return 1

    print("Real LLM smoke test PASSED.")
    print("Direct ModelGateway and required business chains did not return [mock].")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())