from app.services.content_review_service import ContentReviewService


def test_content_review_should_fail_when_sensitive_words_hit() -> None:
    service = ContentReviewService()

    result = service.run_rule_check(
        content="全网第一，百分百治愈，绝对安全",
        brand="智营",
        content_type="product_title",
    )

    assert result.passed is False
    assert result.review_status == "failed"
    assert result.risk_level == "high"
    assert "全网第一" in result.sensitive_check.matched_words


def test_content_review_should_pass_for_safe_product_title() -> None:
    service = ContentReviewService()

    result = service.run_rule_check(
        content="智营智能恒温电热水壶，支持多档控温，适合日常泡茶和冲奶",
        brand="智营",
        content_type="product_title",
    )

    assert result.passed is True
    assert result.review_status == "passed"
    assert result.risk_level == "low"


def test_content_review_should_require_manual_review_when_brand_rule_violated() -> None:
    service = ContentReviewService()

    result = service.run_rule_check(
        content="智能恒温电热水壶，适合家庭与办公室使用",
        brand="智营",
        content_type="product_title",
    )

    assert result.passed is False
    assert result.review_status == "manual_required"
    assert result.brand_check.passed is False
    assert "商品标题未包含品牌名称" in result.brand_check.violations
