# 模块交接文档：执行窗口 10 - 内容生成与审核流

## 一、本窗口目标

执行窗口 10 负责实现电商运营内容生成与审核闭环，覆盖：

- 商品标题生成；
- 商品卖点生成；
- 商品详情页文案生成；
- 活动文案生成；
- 内容规则审核；
- 内容资产版本记录；
- 审核动作留痕；
- 人工提交审核；
- 人工审批通过；
- 内容资产与模型调用日志关联；
- 只做到 `approved` 可发布状态，不做真实发布。

---

## 二、总控裁决执行情况

### 2.1 已遵守

1. 新增 `content_asset` / `content_review` 两张表，并新增 Alembic migration；
2. 未新增 `campaign` 活动表，活动文案第一版使用 `campaign_context` JSON 输入；
3. 未新增敏感词表 / 品牌规则表，第一版规则内置在 `ContentReviewService`；
4. 内容生成走 `PromptService(scene=content_generation)`；
5. 内容生成走 `ModelGateway`；
6. 生成内容形成 `content_asset` 版本记录；
7. 审核动作形成 `content_review` 记录；
8. 生成完成不等于发布，本窗口只做到 `approved` 可发布状态；
9. 商品相关内容通过 `ProductService` 获取商品信息，没有直接查库；
10. `agents/content_generation` 只做轻量受控编排，不做自由 Agent；
11. 已提供 service 测试、API 测试、Alembic migration 说明和全量测试结果；
12. 10B 补丁已完成：生成内容后尽量回填 `content_asset.model_call_log_id`，并在 `metadata_json` 中记录关联状态。

---

## 三、数据库变更

新增 migration：

```text
backend/alembic/versions/d62c219e9482_create_content_asset_and_review.py
```

当前数据库版本已升级到：

```text
d62c219e9482 (head)
```

---

### 3.1 新增表：`content_asset`

用于保存生成内容资产与版本记录。

核心字段：

```text
tenant_id
asset_group_id
version
content_type
biz_type
biz_id
title
content
status
review_status
source
prompt_template_id
prompt_version_id
model_call_log_id
generation_input_json
generation_output_json
rule_check_result_json
metadata_json
created_by
approved_by
approved_at
deleted_at
```

---

### 3.2 新增表：`content_review`

用于保存审核动作与审核结果。

核心字段：

```text
tenant_id
content_asset_id
review_type
review_status
reviewer_type
reviewer_id
sensitive_check_result_json
brand_check_result_json
model_review_result_json
comments
request_id
created_at
```

---

## 四、新增 / 修改文件

### 4.1 Models

```text
backend/app/models/content_asset.py
backend/app/models/content_review.py
backend/app/models/__init__.py
```

---

### 4.2 Repositories

```text
backend/app/repositories/content_asset_repository.py
backend/app/repositories/content_review_repository.py
```

---

### 4.3 Schemas

```text
backend/app/schemas/content.py
```

---

### 4.4 Services

```text
backend/app/services/content_generation_service.py
backend/app/services/content_review_service.py
```

---

### 4.5 Controlled Agent Workflow

```text
backend/app/agents/content_generation/__init__.py
backend/app/agents/content_generation/state.py
backend/app/agents/content_generation/service.py
```

---

### 4.6 API

```text
backend/app/api/v1/content.py
backend/app/api/v1/router.py
```

---

### 4.7 Tests

```text
backend/tests/test_content_review_service.py
backend/tests/test_content_generation_service.py
backend/tests/test_content_api.py
```

---

## 五、API 能力

新增路由前缀：

```text
/api/v1/content
```

---

### 5.1 生成类接口

```http
POST /api/v1/content/generate/product-title
POST /api/v1/content/generate/product-selling-points
POST /api/v1/content/generate/product-detail
POST /api/v1/content/generate/campaign-copy
```

---

### 5.2 审核类接口

```http
POST /api/v1/content/review
POST /api/v1/content/assets/{asset_id}/submit-review
POST /api/v1/content/assets/{asset_id}/approve
POST /api/v1/content/assets/{asset_id}/reject
```

---

### 5.3 查询类接口

```http
GET /api/v1/content/assets/{asset_id}
GET /api/v1/content/assets/{asset_group_id}/versions
```

---

## 六、核心链路

### 6.1 商品内容生成链路

```text
ProductService
  -> PromptService(scene=content_generation)
  -> ModelGateway
  -> 反查 model_call_log
  -> ContentReviewService
  -> content_asset
  -> content_review
```

---

### 6.2 活动文案生成链路

```text
campaign_context JSON
  -> PromptService(scene=content_generation)
  -> ModelGateway
  -> 反查 model_call_log
  -> ContentReviewService
  -> content_asset
  -> content_review
```

---

### 6.3 审核状态流

```text
draft / manual_required
  -> submit-review
reviewing / manual_required
  -> approve
approved / passed
```

拒绝流：

```text
reviewing / manual_required
  -> reject
rejected / failed
```

---

## 七、10B 补丁：`content_asset` 与 `model_call_log` 强关联

### 7.1 背景

窗口 10 主链路完成后，`ModelGateway` 已经可以写入 `model_call_log`，但初版 `content_asset.model_call_log_id` 没有强关联。

10B 小补丁目标是在不重构 `ModelGateway.chat()` 返回结构、不修改 `model_call_log` 表结构、不新增表的前提下，让生成内容资产尽量关联本次模型调用日志。

---

### 7.2 禁止项遵守情况

未修改：

```text
ModelGateway
客服 Agent
导购 Agent
运营 Copilot
model_call_log 表结构
发布模块
```

未新增：

```text
新表
新发布能力
新 Agent 自主规划能力
```

---

### 7.3 实现方式

内容生成调用 `ModelGateway` 后，`ContentGenerationService` 通过以下条件反查最近一次 `model_call_log`：

```text
tenant_id
request_id
prompt_template_id
prompt_version_id
provider
model_name
call_type = chat
created_at >= lookup_started_at - 30s
```

查询成功时：

```text
content_asset.model_call_log_id = model_call_log.id
metadata_json.model_call_log_link_status = linked
```

查询失败时：

```text
content_asset.model_call_log_id = null
metadata_json.model_call_log_link_status = not_found
```

查询失败不会阻塞内容生成，避免日志关联失败影响主业务链路。

---

### 7.4 当前验证结果

商品标题生成接口已返回：

```text
model_call_log_id 非空
metadata_json.model_call_log_link_status = linked
```

示例：

```text
model_call_log_id = 05e5ac64-9d40-421c-a846-63307a790922
model_call_log_link_status = linked
```

---

## 八、手工验证结果

### 8.1 健康检查

通过：

```http
GET /api/v1/health
```

结果：

```text
success = true
database = ok
redis = ok
```

---

### 8.2 规则审核 API

通过：

```http
POST /api/v1/content/review
```

高风险内容示例：

```text
全网第一，百分百治愈，绝对安全
```

返回结果：

```text
rule_check.passed = false
review_status = failed
risk_level = high
```

---

### 8.3 商品标题生成

通过：

```http
POST /api/v1/content/generate/product-title
```

结果：

```text
content_type = product_title
biz_type = product
biz_id = P100001
version = 1
status = draft
review_status = manual_required
review_type = rule_check
reviewer_type = system
model_call_log_id 非空
metadata_json.model_call_log_link_status = linked
```

---

### 8.4 商品卖点生成

通过：

```http
POST /api/v1/content/generate/product-selling-points
```

结果：

```text
content_type = product_selling_points
biz_type = product
biz_id = P100001
status = draft
review_status = manual_required
```

---

### 8.5 商品详情页文案生成

通过：

```http
POST /api/v1/content/generate/product-detail
```

结果：

```text
content_type = product_detail
biz_type = product
biz_id = P100001
status = draft
review_status = manual_required
```

---

### 8.6 活动文案生成

通过：

```http
POST /api/v1/content/generate/campaign-copy
```

结果：

```text
content_type = campaign_copy
biz_type = campaign
biz_id = 五一小家电促销
status = draft
review_status = manual_required
model_call_log_id 非空
metadata_json.model_call_log_link_status = linked
```

---

### 8.7 人工审核流

已验证：

```text
draft / manual_required
  -> submit-review
reviewing / manual_required
  -> approve
approved / passed
```

数据库验证结果：

```text
product_title | P100001 | version=1 | status=approved | review_status=passed | approved_by=reviewer_demo
```

审核记录验证结果：

```text
rule_check    | manual_required | system
manual_review | manual_required | human | operator_demo
manual_review | passed          | human | reviewer_demo
```

---

## 九、自动化测试结果

### 9.1 窗口 10 原始专属测试

```bash
python -m pytest tests/test_content_review_service.py tests/test_content_generation_service.py tests/test_content_api.py -q
```

曾验证通过：

```text
11 passed
```

---

### 9.2 10B 指定测试

```bash
python -m pytest tests/test_content_generation_service.py tests/test_content_api.py -q
```

结果：

```text
10 passed in 1.43s
```

---

### 9.3 全量测试

```bash
python -m pytest tests/ -q
```

结果：

```text
107 passed, 1 warning in 19.81s
```

warning：

```text
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
```

该 warning 在窗口 10 前已存在，不是窗口 10 / 10B 新增阻塞问题。

---

## 十、关键实现说明

### 10.1 为什么 `content_asset` 和 `content_review` 分表

`content_asset` 保存：

```text
内容是什么
内容当前状态
```

`content_review` 保存：

```text
谁在什么时候做了什么审核动作
```

这样可以避免把审核流水塞进内容资产表，后续可以支持：

- 多轮审核；
- 系统审核；
- 人工审核；
- 模型辅助审核；
- 审计追踪。

---

### 10.2 为什么活动文案不新增 `campaign` 表

总控裁决第一版不做活动域建模。

因此活动文案通过：

```text
campaign_name
campaign_context JSON
requirements
tone
```

完成生成上下文传入。

资产记录方式：

```text
content_asset.biz_type = campaign
content_asset.biz_id = campaign_name
```

这已经足够支撑第一版内容资产沉淀。

---

### 10.3 为什么规则内置在 `ContentReviewService`

第一版审核规则稳定、数量少，直接内置可以降低表设计和后台配置复杂度。

当前覆盖：

- 敏感词 / 高风险表达；
- 绝对化营销表达；
- 医疗、金融、法律等效果承诺风险；
- 商品标题品牌名称校验；
- 商品标题长度校验；
- 竞品攻击表达。

后续如果规则变多，再抽象成：

```text
敏感词表
品牌规则表
规则引擎
```

---

### 10.4 为什么 `ProductService` 必须复用

商品相关内容不能直接查库，统一通过：

```text
ProductService.get_product_detail(...)
```

获取商品上下文。

这样可以复用商品服务已有的：

- 数据组装；
- 租户隔离；
- 业务口径；
- 异常处理。

避免内容模块绕过商品服务造成重复逻辑。

---

### 10.5 为什么使用 `PromptService + ModelGateway`

内容生成不是硬编码 Prompt，而是走：

```text
PromptService(scene=content_generation)
ModelGateway
```

这样生成模板、模型供应商、模型调用日志和后续灰度策略都可以复用已有大模型基础设施。

---

### 10.6 为什么 `model_call_log_id` 通过反查关联

总控要求不大改 `ModelGateway.chat()` 返回结构。

因此 10B 选择在 `ContentGenerationService` 内，通过本次生成请求的稳定上下文反查最近一次模型调用日志：

```text
request_id
prompt_template_id
prompt_version_id
provider
model_name
created_at
```

这样可以补上：

```text
content_asset -> model_call_log
```

的强关联，同时不影响窗口 4 的模型网关设计。

---

### 10.7 为什么查不到日志不阻塞生成

模型调用日志关联是可观测性增强，不应该反过来阻断内容生成主链路。

因此查不到日志时：

```text
content_asset.model_call_log_id = null
metadata_json.model_call_log_link_status = not_found
```

业务仍正常生成内容和审核记录。

---

### 10.8 为什么 `agents/content_generation` 是轻量编排

本窗口没有做自由 Agent，也没有做自主工具规划。

`agents/content_generation` 只记录受控流程状态：

```text
generate -> review -> persist
```

真实业务逻辑仍放在 `ContentGenerationService`，避免 Agent 层失控膨胀。

---

## 十一、已知问题 / 后续建议

### 11.1 mock provider 输出特性

当前 mock provider 会把完整 Prompt 回显为模型输出，导致生成内容偏长，规则审核经常进入：

```text
manual_required
```

这不是内容审核链路失败，而是 mock provider 的测试输出特性。

接入真实模型后，输出会更接近实际营销文案。

---

### 11.2 事务边界

当前 `ModelCallLogService` 内部会独立 commit 模型调用日志，随后 `ContentGenerationService` 再写入 `content_asset`
和 `content_review`。

这意味着模型日志和内容资产不是完全同一个事务边界。

当前可接受，但后续如需强一致性，需要统一事务设计。

---

### 11.3 当前版本策略

当前生成内容每次创建新的 `asset_group_id`，`version = 1`。

本窗口已完成“生成内容形成版本记录”的基础结构，但还没有实现同一 `asset_group_id` 下重新生成并递增 `version` 的完整能力。

后续如果需要内容重生成 / 多版本对比，可以在现有：

```text
content_asset.asset_group_id + version
```

上继续扩展。

---

## 十二、交接结论

执行窗口 10 已完成电商运营内容生成与审核闭环。

当前已经具备：

1. 商品标题生成；
2. 商品卖点生成；
3. 商品详情页文案生成；
4. 活动文案生成；
5. 内容规则审核；
6. 内容资产版本记录；
7. 审核动作留痕；
8. 人工提交审核；
9. 人工审批通过；
10. 内容资产与模型调用日志关联；
11. 只做到 `approved` 可发布状态，不做真实发布；
12. service 测试、API 测试和全量测试通过。

最终验收结果：

```text
窗口 10 原始专属测试：11 passed
10B 指定测试：10 passed in 1.43s
全量测试：107 passed, 1 warning in 19.81s
```

结论：

```text
窗口 10 当前可以交付。
10B 补丁已完成。
未做真实发布。
未新增 campaign 表。
未新增敏感词表 / 品牌规则表。
未绕过 ProductService。
未绕过 PromptService / ModelGateway。
未修改客服 Agent、导购 Agent、运营 Copilot。
```