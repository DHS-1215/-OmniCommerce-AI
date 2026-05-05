import os
from typing import Any

import httpx

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BASE_URL = os.getenv(
    "TEST_API_BASE_URL",
    os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
)


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = httpx.post(
        f"{BASE_URL}{path}",
        json=payload,
        timeout=60,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "success" in data
    assert "code" in data
    assert "message" in data
    assert "data" in data
    assert "request_id" in data
    return data


def _get(path: str) -> dict[str, Any]:
    response = httpx.get(
        f"{BASE_URL}{path}",
        timeout=30,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    return data


def test_content_review_api_should_detect_high_risk_content() -> None:
    data = _post(
        "/api/v1/content/review",
        {
            "tenant_id": TENANT_ID,
            "content": "全网第一，百分百治愈，绝对安全",
            "brand": "智营",
            "content_type": "product_title",
            "enable_model_review": False,
        },
    )

    assert data["success"] is True
    rule_check = data["data"]["rule_check"]
    assert rule_check["passed"] is False
    assert rule_check["review_status"] == "failed"
    assert rule_check["risk_level"] == "high"


def test_content_review_api_should_pass_safe_content() -> None:
    data = _post(
        "/api/v1/content/review",
        {
            "tenant_id": TENANT_ID,
            "content": "智营智能恒温电热水壶，支持多档控温，适合日常泡茶和冲奶",
            "brand": "智营",
            "content_type": "product_title",
            "enable_model_review": False,
        },
    )

    assert data["success"] is True
    rule_check = data["data"]["rule_check"]
    assert rule_check["passed"] is True
    assert rule_check["review_status"] == "passed"


def test_content_generate_product_title_should_create_asset_and_review() -> None:
    data = _post(
        "/api/v1/content/generate/product-title",
        {
            "tenant_id": TENANT_ID,
            "product_no": "P100001",
            "requirements": "突出智能恒温和礼品属性",
            "tone": "简洁、有转化感",
            "created_by": "pytest_content",
        },
    )

    assert data["success"] is True
    asset = data["data"]["asset"]
    review = data["data"]["review"]

    assert asset["content_type"] == "product_title"
    assert asset["biz_type"] == "product"
    assert asset["biz_id"] == "P100001"
    assert asset["version"] == 1
    assert asset["status"] == "draft"
    assert asset["source"] == "llm_generated"
    assert asset["prompt_template_id"] is not None
    assert asset["prompt_version_id"] is not None

    assert asset["model_call_log_id"] is not None
    assert asset["metadata_json"]["model_call_log_link_status"] == "linked"

    assert asset["generation_input_json"] is not None
    assert asset["generation_output_json"] is not None
    assert asset["rule_check_result_json"] is not None

    assert review["review_type"] == "rule_check"
    assert review["reviewer_type"] == "system"


def test_content_generate_campaign_copy_should_use_campaign_context_without_campaign_table() -> None:
    data = _post(
        "/api/v1/content/generate/campaign-copy",
        {
            "tenant_id": TENANT_ID,
            "campaign_name": "pytest 五一小家电促销",
            "campaign_context": {
                "discount": "满300减50",
                "target_user": "新会员",
                "channel": "首页 Banner",
            },
            "requirements": "突出限时优惠和小家电换新场景",
            "tone": "简洁、有促销氛围",
            "created_by": "pytest_content",
        },
    )

    assert data["success"] is True
    asset = data["data"]["asset"]
    review = data["data"]["review"]

    assert asset["content_type"] == "campaign_copy"
    assert asset["biz_type"] == "campaign"
    assert asset["biz_id"] == "pytest 五一小家电促销"
    assert asset["status"] == "draft"
    assert asset["generation_input_json"]["variables"]["campaign_context"]["discount"] == "满300减50"

    assert review["review_type"] == "rule_check"
    assert review["reviewer_type"] == "system"

    assert asset["model_call_log_id"] is not None
    assert asset["metadata_json"]["model_call_log_link_status"] == "linked"


def test_content_manual_review_flow_should_submit_and_approve() -> None:
    generated = _post(
        "/api/v1/content/generate/product-title",
        {
            "tenant_id": TENANT_ID,
            "product_no": "P100001",
            "requirements": "突出智能恒温和礼品属性",
            "tone": "简洁、有转化感",
            "created_by": "pytest_content",
        },
    )

    asset = generated["data"]["asset"]
    asset_id = asset["id"]
    asset_group_id = asset["asset_group_id"]

    submitted = _post(
        f"/api/v1/content/assets/{asset_id}/submit-review",
        {
            "tenant_id": TENANT_ID,
            "operator_id": "pytest_operator",
            "comments": "提交人工审核",
        },
    )

    submitted_asset = submitted["data"]["asset"]
    submitted_review = submitted["data"]["review"]

    assert submitted_asset["status"] == "reviewing"
    assert submitted_asset["review_status"] == "manual_required"
    assert submitted_review["review_type"] == "manual_review"
    assert submitted_review["review_status"] == "manual_required"
    assert submitted_review["reviewer_type"] == "human"

    approved = _post(
        f"/api/v1/content/assets/{asset_id}/approve",
        {
            "tenant_id": TENANT_ID,
            "reviewer_id": "pytest_reviewer",
            "comments": "审核通过，可进入待发布状态",
        },
    )

    approved_asset = approved["data"]["asset"]
    approved_review = approved["data"]["review"]

    assert approved_asset["status"] == "approved"
    assert approved_asset["review_status"] == "passed"
    assert approved_asset["approved_by"] == "pytest_reviewer"
    assert approved_review["review_type"] == "manual_review"
    assert approved_review["review_status"] == "passed"

    detail = _get(f"/api/v1/content/assets/{asset_id}?tenant_id={TENANT_ID}")
    assert detail["data"]["id"] == asset_id
    assert detail["data"]["status"] == "approved"

    versions = _get(f"/api/v1/content/assets/{asset_group_id}/versions?tenant_id={TENANT_ID}")
    assert versions["data"]["asset_group_id"] == asset_group_id
    assert versions["data"]["total"] >= 1
