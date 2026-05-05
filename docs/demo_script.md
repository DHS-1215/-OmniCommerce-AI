# 最终演示脚本

本文档用于最终演示智营 OmniCommerce AI 的核心链路。每条演示都包含请求命令、预期关键字段、日志查询 SQL 和面试讲解点。

## 0. 演示前准备

统一变量：

~~~powershell
cd D:\omni-commerce-ai
$TENANT_ID="00000000-0000-0000-0000-000000000001"
$BASE_URL="http://127.0.0.1:8002"
~~~

健康检查：

~~~powershell
curl.exe "$BASE_URL/api/v1/health"
~~~

预期：

~~~text
success = true
data.status = ok
data.database = ok
data.redis = ok
~~~

## 1. 商品查询

请求：

~~~powershell
curl.exe "$BASE_URL/api/v1/products/P100001?tenant_id=$TENANT_ID"
~~~

预期关键字段：

~~~text
success = true
data.product_no = P100001
data.status = active
data.title 非空
~~~

相关日志查询：

~~~sql
select product_no, title, brand, category, status, created_at
from product
where product_no = 'P100001';
~~~

面试讲解点：

> 基础业务服务层采用 API / schemas / services / repositories / models 分层。商品查询不会直接在 API 层写 SQL，而是通过
> ProductService 和 ProductRepository 复用统一业务口径。

## 2. RAG 政策问答

准备请求文件：

~~~powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "question": "七天无理由退货有哪些条件？",
  "top_k": 5
}
'@ | Set-Content -Encoding utf8 .\tmp_rag_ask.json
~~~

请求：

~~~powershell
curl.exe -X POST "$BASE_URL/api/v1/knowledge/ask" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_rag_ask.json"
~~~

预期关键字段：

~~~text
success = true
data.answer 非空
data.citations 非空
data.prompt_template_id 非空
data.prompt_version_id 非空
~~~

相关日志查询：

~~~sql
select query, retrieval_mode, result_count, latency_ms, request_id, created_at
from rag_retrieval_log
order by created_at desc limit 5;
~~~

面试讲解点：

> RAG 不是只让模型回答，而是通过 Qdrant + OpenSearch 混合检索拿到 chunk，再由 CitationBuilder 返回引用来源，并写入
> rag_retrieval_log 方便追溯。

## 3. 客服 Agent：订单查询

准备请求文件：

~~~powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "demo_cs_order_001",
  "user_no": "U100001",
  "message": "我的订单 O100001 到哪了？",
  "conversation_summary": "",
  "context": {
    "order_no": "O100001"
  }
}
'@ | Set-Content -Encoding utf8 .\tmp_cs_order.json
~~~

请求：

~~~powershell
curl.exe -X POST "$BASE_URL/api/v1/agents/customer-service/chat" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_cs_order.json"
~~~

预期关键字段：

~~~text
data.intent = order_query
data.handoff_required = false
data.tool_calls 包含 get_order_detail
data.answer 包含订单状态
~~~

相关日志查询：

~~~sql
select agent_type, task_no, intent, status, handoff_required, request_id, created_at
from agent_task
order by created_at desc limit 5;

select tool_name, tool_type, status, input_summary, output_summary, created_at
from tool_call_log
order by created_at desc limit 10;
~~~

面试讲解点：

> 客服 Agent 不是自由聊天，而是 LangGraph 编排：意图识别、工具调用、风险校验、回答生成、任务收尾，每一步都有日志。

## 4. 客服 Agent：投诉转人工

准备请求文件：

~~~powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "demo_cs_complaint_001",
  "user_no": "U100001",
  "message": "我要投诉，你们不给我赔偿我就曝光",
  "conversation_summary": "",
  "context": {}
}
'@ | Set-Content -Encoding utf8 .\tmp_cs_complaint.json
~~~

请求：

~~~powershell
curl.exe -X POST "$BASE_URL/api/v1/agents/customer-service/chat" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_cs_complaint.json"
~~~

预期关键字段：

~~~text
data.intent = complaint
data.handoff_required = true
data.tool_calls 包含 create_customer_service_ticket
~~~

相关日志查询：

~~~sql
select agent_type, intent, status, handoff_required, input_summary, output_summary, created_at
from agent_task
where agent_type = 'customer_service'
order by created_at desc limit 5;

select tool_name, tool_type, status, input_summary, output_summary, created_at
from tool_call_log
where tool_name = 'create_customer_service_ticket'
order by created_at desc limit 5;
~~~

面试讲解点：

> 高风险场景不能完全交给模型判断。项目中通过规则护栏优先识别投诉、赔付、曝光等风险表达，并自动创建工单转人工。

## 5. 导购 Agent：预算推荐

准备请求文件：

~~~powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "demo_sg_budget_001",
  "user_no": "U100001",
  "message": "我预算 300 元以内，想买一个适合办公室用的智能小家电，最好安全、省心、评价好一点",
  "conversation_summary": "",
  "context": {
    "budget_max": 300,
    "scenario": "office",
    "preferences": ["安全", "省心", "评价好"]
  }
}
'@ | Set-Content -Encoding utf8 .\tmp_sg_budget.json
~~~

请求：

~~~powershell
curl.exe -X POST "$BASE_URL/api/v1/agents/shopping-guide/chat" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_sg_budget.json"
~~~

预期关键字段：

~~~text
data.intent = shopping_guide
data.recommendations 非空
data.recommendations[0].match_evidence 非空
data.tool_calls 包含 parse_user_need / recall_product_candidates
~~~

相关日志查询：

~~~sql
select tool_name, tool_type, status, input_summary, output_summary, created_at
from tool_call_log
where tool_type = 'recommendation'
order by created_at desc limit 10;
~~~

面试讲解点：

> 导购 Agent 不让 LLM 编造商品、价格、库存。候选商品、SKU、价格、库存、评价来自真实 ProductService，LLM 只用于表达润色。

## 6. 导购 Agent：指定商品 SKU 对比

准备请求文件：

~~~powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "demo_sg_compare_001",
  "user_no": "U100001",
  "message": "帮我对比一下 P100001 这个商品有哪些规格，适合办公室用吗？",
  "conversation_summary": "",
  "context": {
    "product_no": "P100001",
    "scenario": "office"
  }
}
'@ | Set-Content -Encoding utf8 .\tmp_sg_compare.json
~~~

请求：

~~~powershell
curl.exe -X POST "$BASE_URL/api/v1/agents/shopping-guide/chat" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_sg_compare.json"
~~~

预期关键字段：

~~~text
data.intent = sku_compare 或 shopping_guide
data.comparisons 或 data.recommendations 非空
data.tool_calls 包含 compare_product_skus 或 recall_product_candidates
~~~

相关日志查询：

~~~sql
select agent_type, intent, status, input_summary, output_summary, created_at
from agent_task
where agent_type = 'shopping_guide'
order by created_at desc limit 10;
~~~

面试讲解点：

> 用户明确指定 product_no 时，导购 Agent 优先围绕指定商品做 SKU 对比，不会转而推荐数据库里其他商品。

## 7. 运营 Copilot：GMV 查询

准备请求文件：

~~~powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "demo_op_gmv_001",
  "user_no": "U100001",
  "message": "帮我查询一下 GMV",
  "conversation_summary": "",
  "context": {
    "metric_key": "gmv"
  }
}
'@ | Set-Content -Encoding utf8 .\tmp_op_gmv.json
~~~

请求：

~~~powershell
curl.exe -X POST "$BASE_URL/api/v1/agents/operation-copilot/chat" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_op_gmv.json"
~~~

预期关键字段：

~~~text
data.intent = metric_query
data.sql_summary.guard.passed = true
data.query_result.row_count >= 1
~~~

相关日志查询：

~~~sql
select tool_name, tool_type, status, input_summary, output_summary, created_at
from tool_call_log
where tool_type = 'bi'
order by created_at desc limit 10;
~~~

面试讲解点：

> 运营 Copilot 最大亮点不是让模型裸写 SQL，而是 SQL Guard 强制检查，只允许白名单表、只读查询、tenant_id 过滤、最大行数限制。

## 8. 运营 Copilot：低库存分析

准备请求文件：

~~~powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "demo_op_low_stock_001",
  "user_no": "U100001",
  "message": "帮我看一下低库存 SKU 数量",
  "conversation_summary": "",
  "context": {
    "metric_key": "low_stock_sku_count"
  }
}
'@ | Set-Content -Encoding utf8 .\tmp_op_low_stock.json
~~~

请求：

~~~powershell
curl.exe -X POST "$BASE_URL/api/v1/agents/operation-copilot/chat" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_op_low_stock.json"
~~~

预期关键字段：

~~~text
data.intent = metric_query
data.sql_summary.guard.passed = true
data.query_result 非空
~~~

面试讲解点：

> 指标不是临时拼 SQL，而是 MetricService 管理指标口径，SQL Guard 保证查询安全。

## 9. 内容生成：商品标题生成

准备请求文件：

~~~powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "product_no": "P100001",
  "requirements": "突出办公室使用、安全、省心、智能控温",
  "tone": "专业可信"
}
'@ | Set-Content -Encoding utf8 .\tmp_content_title.json
~~~

请求：

~~~powershell
curl.exe -X POST "$BASE_URL/api/v1/content/generate/product-title" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_content_title.json"
~~~

预期关键字段：

~~~text
data.content_type = product_title
data.biz_type = product
data.biz_id = P100001
data.status = draft
data.review_status = manual_required 或 passed
data.model_call_log_id 可能非空
~~~

相关日志查询：

~~~sql
select content_type,
       biz_type,
       biz_id,
       version,
       status,
       review_status,
       model_call_log_id,
       created_at
from content_asset
order by created_at desc limit 10;

select review_type, review_status, reviewer_type, comments, created_at
from content_review
order by created_at desc limit 10;
~~~

面试讲解点：

> 内容生成不是生成完直接发布，而是形成 content_asset 版本记录，再经过规则审核和人工审核，最终只做到 approved 可发布状态。

## 10. 内容审核：提交审核与审批通过

先从上一步响应中拿到 `content_asset.id`。

提交审核：

~~~powershell
curl.exe -X POST "$BASE_URL/api/v1/content/assets/{asset_id}/submit-review" `
  -H "Content-Type: application/json" `
  --data-binary "{}"
~~~

审批通过：

~~~powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "reviewer_id": "reviewer_demo",
  "comments": "演示审批通过"
}
'@ | Set-Content -Encoding utf8 .\tmp_content_approve.json

curl.exe -X POST "$BASE_URL/api/v1/content/assets/{asset_id}/approve" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_content_approve.json"
~~~

预期关键字段：

~~~text
status = approved
review_status = passed
approved_by = reviewer_demo
~~~

面试讲解点：

> content_asset 保存内容当前状态，content_review 保存审核动作流水。这样后续可以支持多轮审核、系统审核、人工审核和审计追踪。

## 生产化认证 / RBAC / 租户隔离演示

本演示用于展示 v1.1 的轻量生产化增强能力：登录态、JWT、角色权限和租户隔离。

### 1. 启用认证模式

```powershell
cd D:\omni-commerce-ai

$env:AUTH_ENABLED="true"
docker compose up -d --build backend

docker compose exec backend python -c "from app.core.config import get_settings; s=get_settings(); print('AUTH_ENABLED=', s.auth_enabled)"
```

确认输出：

```text
AUTH_ENABLED= True
```

### 2. 初始化本地 demo 账号

```powershell
docker compose exec backend python scripts/seed_auth_accounts.py
```

默认账号：

| username | password    | role     |
|----------|-------------|----------|
| admin    | admin123    | admin    |
| operator | operator123 | operator |
| viewer   | viewer123   | viewer   |

这些账号仅用于本地演示，不得用于生产环境。

### 3. 登录并查看当前用户

```powershell
$BASE_URL="http://127.0.0.1:8002"

@'
{
  "username": "admin",
  "password": "admin123"
}
'@ | Set-Content -Encoding utf8 .\tmp_auth_login.json

$response = curl.exe -s -X POST "$BASE_URL/api/v1/auth/login" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_auth_login.json" | ConvertFrom-Json

$TOKEN=$response.data.access_token

curl.exe "$BASE_URL/api/v1/auth/me" `
  -H "Authorization: Bearer $TOKEN"
```

预期结果：

- `/api/v1/auth/login` 返回 `access_token`；
- `/api/v1/auth/me` 返回当前用户；
- token claims 中包含 `user_id`、`user_no`、`tenant_id`、`role`、`exp`。

注意：演示时不要把完整 token 粘贴到文档、聊天窗口或提交记录中。

### 4. RBAC 拦截演示

operator / viewer 访问 admin 写接口应返回 403：

```powershell
cd D:\omni-commerce-ai\backend

$env:AUTH_ENABLED="true"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/test_rbac_api.py -q
```

预期结果：

```text
4 passed
```

该测试覆盖：

- operator 访问 Prompt admin 写接口被拒绝；
- viewer 访问 Prompt admin 写接口被拒绝；
- token tenant_id 与请求 tenant_id 不一致时返回 403；
- admin 通过 RBAC 后进入业务层。

### 5. 恢复默认兼容模式

演示结束后恢复默认模式，保证旧测试和旧演示不受影响：

```powershell
cd D:\omni-commerce-ai

$env:AUTH_ENABLED="false"
docker compose up -d --build backend

docker compose exec backend python -c "from app.core.config import get_settings; s=get_settings(); print('AUTH_ENABLED=', s.auth_enabled)"
```

确认输出：

```text
AUTH_ENABLED= False
```

## 11. 评测中心：查询评测结果

查询最近评测结果：

~~~powershell
curl.exe "$BASE_URL/api/v1/evaluations/results?tenant_id=$TENANT_ID&page=1&page_size=10"
~~~

查询评测报告：

~~~powershell
curl.exe "$BASE_URL/api/v1/evaluations/report?tenant_id=$TENANT_ID"
~~~

SQL 查询：

~~~sql
select target_type,
       target_id,
       status,
       run_no,
       score,
       tool_call_success_rate,
       agent_task_success_rate,
       created_at
from evaluation_result
order by created_at desc limit 20;
~~~

面试讲解点：

> 项目不仅实现 RAG 和 Agent，还补了评测中心，用 evaluation_case / evaluation_result 记录用例、执行结果和指标，支撑
> Prompt、RAG、Agent 的效果对比。

## 12. 可观测性总览查询

模型调用：

~~~sql
select provider, model_name, call_type, status, latency_ms, request_id, created_at
from model_call_log
order by created_at desc limit 10;
~~~

RAG 检索：

~~~sql
select query, retrieval_mode, result_count, latency_ms, request_id, created_at
from rag_retrieval_log
order by created_at desc limit 10;
~~~

Agent 任务：

~~~sql
select agent_type, task_no, intent, status, handoff_required, request_id, created_at
from agent_task
order by created_at desc limit 10;
~~~

工具调用：

~~~sql
select tool_name, tool_type, status, latency_ms, created_at
from tool_call_log
order by created_at desc limit 10;
~~~

内容资产：

~~~sql
select content_type,
       biz_type,
       biz_id,
       version,
       status,
       review_status,
       model_call_log_id,
       created_at
from content_asset
order by created_at desc limit 10;
~~~

## 13. 演示后清理临时文件

如果不想保留临时请求文件，可以执行：

~~~powershell
Remove-Item .\tmp_*.json -ErrorAction SilentlyContinue
~~~

注意：如果某些 `tmp_*.json` 已经被 Git 跟踪，不要直接删除后提交。可以执行：

~~~powershell
git checkout -- tmp_*.json
~~~

避免最终提交里混入无关删除。