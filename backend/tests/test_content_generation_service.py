from uuid import uuid4

from app.services.content_generation_service import ContentGenerationService


def test_content_generation_json_safe_should_convert_uuid_to_string() -> None:
    service = ContentGenerationService()
    raw_id = uuid4()

    result = service._json_safe(
        {
            "id": raw_id,
            "nested": {
                "ids": [raw_id],
            },
        }
    )

    assert result["id"] == str(raw_id)
    assert result["nested"]["ids"][0] == str(raw_id)


def test_content_generation_should_build_prompt_variables_for_product() -> None:
    service = ContentGenerationService()

    product_context = {
        "product_no": "P100001",
        "title": "智营智能恒温电热水壶",
        "brand": "智营",
        "category": "smart_home",
        "attribute_json": {
            "capacity": "1.7L",
        },
    }

    variables = service._build_product_variables(
        content_type="product_title",
        product_context=product_context,
        requirements="突出智能恒温",
        tone="简洁",
        output_format="生成商品标题",
    )

    assert variables["scene"] == "content_generation"
    assert variables["content_type"] == "product_title"
    assert variables["biz_type"] == "product"
    assert variables["product_no"] == "P100001"
    assert variables["generation_requirement"] == "突出智能恒温"
    assert isinstance(variables["product_info"], str)
    assert isinstance(variables["campaign_info"], str)
    assert "智营智能恒温电热水壶" in variables["product_info"]


def test_content_generation_should_extract_mock_chat_content() -> None:
    service = ContentGenerationService()

    content = service._extract_model_content(
        {
            "provider": "mock",
            "model_name": "mock-chat-model",
            "content": "生成后的文案",
        }
    )

    assert content == "生成后的文案"

def test_content_generation_should_mark_model_call_log_not_found() -> None:
    service = ContentGenerationService()

    metadata = service._build_asset_metadata(
        model_call_log_id=None,
    )

    assert metadata["model_call_log_link_status"] == "not_found"


def test_content_generation_should_mark_model_call_log_linked() -> None:
    service = ContentGenerationService()
    log_id = uuid4()

    metadata = service._build_asset_metadata(
        model_call_log_id=log_id,
    )

    assert metadata["model_call_log_link_status"] == "linked"
