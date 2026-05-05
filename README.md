# 智营 OmniCommerce AI：电商企业级大模型运营中台

## 1. 项目简介

智营 OmniCommerce AI 是一个面向电商企业的大模型应用中台原型，覆盖商品、订单、售后、客服、知识库、Prompt、模型网关、Agent、内容生成、评测中心和可观测性链路。

本项目不是单纯聊天机器人，也不是只展示 LangChain / RAG 的 Demo。它的目标是把企业电商业务对象和大模型能力结合起来，形成一套能运行、能测试、能演示、能排查、能讲清楚的企业级
AI 应用项目。

核心能力包括：

- 电商基础业务：用户、商品、SKU、评价、订单、售后、客服工单
- 模型网关：Mock Provider、OpenAI-compatible Provider、模型调用日志
- Prompt 管理：模板、版本、场景、变量渲染、灰度字段预留
- 企业知识库 RAG：MinIO、Parser、Chunk、Embedding、Qdrant、OpenSearch、引用溯源
- 智能客服 Agent：订单查询、售后查询/申请、政策问答、投诉转人工
- 智能导购 Agent：预算推荐、SKU 对比、评价摘要、推荐理由
- 运营 Copilot：指标口径、SQL Guard、只读 SQL、GMV / 库存 / 售后分析
- 内容生成与审核：商品标题、卖点、详情页、活动文案、规则审核、人工审核
- 评测中心：RAG / Agent / Prompt / 检索策略评测与报告
- 可观测性：request_id、model_call_log、rag_retrieval_log、agent_task、tool_call_log、evaluation_result

## 2. 业务背景

电商企业在经营过程中会面对大量重复但高价值的业务操作：

- 用户咨询订单、商品、售后政策
- 运营人员查询 GMV、库存、售后、评价等指标
- 商家需要生成商品标题、卖点、详情页和活动文案
- 企业知识库需要支持政策问答和引用溯源
- 大模型链路需要被评测、追踪和复盘

传统做法通常是多个孤立系统：业务后台、知识库、数据报表、内容工具、客服系统各自分散。本项目把这些能力整合成一个后端中台，用统一模型网关、Prompt
管理、RAG、Agent 编排、日志审计和评测中心串起来。

## 3. 技术栈

后端与工程：

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x Async
- Alembic
- PostgreSQL 16
- Redis
- Docker / Docker Compose
- pytest / httpx

大模型与智能应用：

- ModelGateway 自研模型网关
- Mock Provider
- OpenAI-compatible Provider
- LangGraph
- PromptService
- RAG 检索与引用生成
- 自定义评测指标

检索与存储：

- PostgreSQL JSONB
- Qdrant
- OpenSearch
- MinIO
- Tesseract OCR 生产依赖预留

## 4. 系统架构

核心链路：

~~~text
API Layer
  -> Service Layer
  -> Repository Layer
  -> PostgreSQL / Redis / MinIO / Qdrant / OpenSearch

PromptService
  -> ModelGateway
  -> model_call_log

KnowledgeService
  -> Parser / Chunker / Embedder
  -> Qdrant + OpenSearch
  -> CitationBuilder
  -> rag_retrieval_log

Agent Service
  -> LangGraph Workflow
  -> Tools
  -> Business Services / RAG / BI Tools
  -> agent_task / agent_step_log / tool_call_log

EvaluationService
  -> RAG / Agent / Prompt / Retrieval targets
  -> evaluation_result
~~~

## 5. 核心模块

### 5.1 基础工程骨架

- 统一响应结构：`success / code / message / data / request_id`
- 统一异常处理
- request_id 中间件
- PostgreSQL / Redis 连接
- Alembic 迁移
- Docker Compose 基础环境

### 5.2 核心数据模型

核心表包括：

- `user_profile`
- `product`
- `product_sku`
- `product_review`
- `order_info`
- `order_item`
- `after_sale_ticket`
- `customer_service_ticket`
- `knowledge_document`
- `knowledge_chunk`
- `prompt_template`
- `prompt_version`
- `model_call_log`
- `agent_task`
- `agent_step_log`
- `tool_call_log`
- `evaluation_case`
- `evaluation_result`
- `content_asset`
- `content_review`
- `rag_retrieval_log`

### 5.3 模型网关

统一入口：

~~~text
backend/app/llm/
ModelGateway
~~~

支持：

- 普通 Chat
- Embedding
- SSE Stream
- Mock Provider
- OpenAI-compatible Provider
- 失败重试
- 错误归一
- 模型调用日志入库

### 5.4 Prompt 管理

支持：

- Prompt 模板 CRUD
- Prompt 版本管理
- 当前启用版本查询
- 按 scene 获取 Prompt
- 变量渲染
- Prompt 调用追踪字段：`prompt_template_id / prompt_version_id`

### 5.5 企业知识库 RAG

支持：

- 文档上传
- MinIO 保存原始文件
- 多格式 Parser
- OCR 抽象
- 文本清洗与切片
- Embedding
- Qdrant 向量检索
- OpenSearch BM25 检索
- HybridRetriever
- CitationBuilder
- RAG 检索日志

### 5.6 客服 Agent

接口：

~~~http
POST /api/v1/agents/customer-service/chat
~~~

能力：

- 订单查询
- 商品咨询
- 售后查询
- 售后申请
- 政策 RAG 问答
- 投诉转人工
- 工单创建
- Agent 日志和工具调用日志

### 5.7 导购 Agent

接口：

~~~http
POST /api/v1/agents/shopping-guide/chat
~~~

能力：

- 预算识别
- 场景识别
- 偏好识别
- 商品候选召回
- SKU 对比
- 评价摘要
- 推荐理由
- 结构化推荐结果

### 5.8 运营 Copilot

接口：

~~~http
POST /api/v1/agents/operation-copilot/chat
~~~

能力：

- 指标口径管理
- GMV / 订单数 / 库存 / 售后 / 评价指标查询
- SQL Guard
- 只读 SQL 执行
- 最大返回行数限制
- 运营报告生成边界预留

### 5.9 内容生成与审核

接口前缀：

~~~http
/api/v1/content
~~~

能力：

- 商品标题生成
- 商品卖点生成
- 商品详情页生成
- 活动文案生成
- 内容规则审核
- 人工提交审核
- 人工审批通过 / 拒绝
- 内容资产版本记录
- 内容资产关联模型调用日志

### 5.10 评测中心

接口前缀：

~~~http
/api/v1/evaluations
~~~

能力：

- 评测用例管理
- RAG 评测
- Agent 评测
- 自定义指标计算
- 评测结果入库
- 评测报告
- Prompt 版本对比
- 检索策略对比

### 5.11 认证 / RBAC / 租户隔离

v1.1 增强了轻量生产化认证能力，用于补齐企业级系统的身份上下文、角色权限和租户隔离边界。

已实现能力：

- 新增 `auth_account` 登录账号表，不污染 `user_profile` 业务画像表；
- 支持用户名 + 密码登录；
- 密码使用 PBKDF2-HMAC-SHA256 hash 存储，不保存明文密码；
- 使用 HS256 JWT 签发登录态；
- JWT claims 包含 `user_id`、`user_no`、`tenant_id`、`role`、`exp`；
- 新增 `/api/v1/auth/login` 和 `/api/v1/auth/me`；
- 新增 `get_current_user`、`get_current_tenant_id`、`require_roles(...)` 依赖；
- 支持 `admin / operator / viewer` 三类角色；
- 认证开启时，`tenant_id` 优先从 token 注入；
- 如果请求中仍显式传入 `tenant_id`，必须与 token 中的 `tenant_id` 一致，否则返回 403；
- 默认 `AUTH_ENABLED=false`，保证旧测试和旧演示兼容；
- 生产化演示可切换 `AUTH_ENABLED=true`，展示登录、RBAC 和租户隔离能力。

当前已接入 RBAC 的关键接口：

- Prompt 写接口：仅 `admin`；
- Knowledge 上传接口：仅 `admin`；
- Content 提交审核：`admin / operator`；
- Content 审批 / 驳回：仅 `admin`；
- Evaluations 执行类接口：仅 `admin`。

为了避免破坏 v1.0 已通过的客服、导购、运营 Copilot 演示主链路，Agent 对话类接口暂未强制接入认证。后续可在前端演示流程稳定后，再逐步开启。

## 6. 启动方式

项目根目录：

~~~powershell
cd D:\omni-commerce-ai
docker compose up -d --build
~~~

查看容器：

~~~powershell
docker compose ps
~~~

健康检查：

~~~powershell
curl.exe "http://127.0.0.1:8002/api/v1/health"
~~~

预期：

~~~json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "status": "ok",
    "database": "ok",
    "redis": "ok"
  },
  "request_id": "req_xxx"
}
~~~

## 7. 端口说明

宿主机访问后端：

~~~text
http://127.0.0.1:8002
~~~

容器内部 Uvicorn：

~~~text
0.0.0.0:8000
~~~

映射关系：

~~~text
8002 -> 8000
~~~

注意：测试如果打到 `127.0.0.1:8000`，可能出现 404。这不是业务失败，是端口打错。

常用服务端口：

| 服务                     | 宿主机端口 |
|------------------------|-------|
| Backend                | 8002  |
| PostgreSQL             | 5432  |
| MinIO S3 API           | 9000  |
| MinIO Console          | 9001  |
| OpenSearch             | 9200  |
| OpenSearch Performance | 9600  |

## 8. 环境变量

默认测试和开发使用 mock 模型：

### 8.1 认证与 JWT

默认开发和测试关闭强制认证：

```env
AUTH_ENABLED=false
JWT_SECRET_KEY=change_me_in_local_env
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

说明：

- `AUTH_ENABLED=false`：兼容旧接口、旧测试和旧演示，接口仍可显式传入 `tenant_id`；
- `AUTH_ENABLED=true`：启用生产化认证模式，关键写接口需要 Bearer Token；
- `JWT_SECRET_KEY` 只能通过本地 `.env` 或临时环境变量注入；
- 不允许把真实 JWT secret 提交到代码、README、测试文件或交接文档；
- `backend/.env` 不进入 Git，只提交 `backend/.env.example`。

~~~env
DEFAULT_LLM_PROVIDER=mock
DEFAULT_LLM_MODEL=mock-chat-model
DEFAULT_EMBEDDING_PROVIDER=mock
DEFAULT_EMBEDDING_MODEL=mock-embedding-model
~~~

真实模型示例：

~~~env
DEFAULT_LLM_PROVIDER=openai_compatible
DEFAULT_LLM_MODEL=qwen-turbo
DEFAULT_EMBEDDING_PROVIDER=openai_compatible
DEFAULT_EMBEDDING_MODEL=text-embedding-v3
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=用户本地自己的 API Key
~~~

安全要求：

- 不要把真实 API Key 写进代码
- 不要提交真实 `.env`
- 不要把真实 Key 写进 README、测试文件或交接文档
- 默认 pytest 不依赖真实模型

## 9. 数据库迁移

进入后端目录：

~~~powershell
cd D:\omni-commerce-ai\backend
python -m alembic current
python -m alembic upgrade head
~~~

当前最终 head：

~~~text
d62c219e9482
~~~

## 10. 种子数据

基础种子数据：

~~~powershell
cd D:\omni-commerce-ai\backend
python scripts/seed_core_data.py
python scripts/seed_demo_scenarios.py
python scripts/seed_prompt_data.py
~~~

### 10.1 认证账号种子数据

v1.1 新增本地认证账号种子脚本：

```powershell
cd D:\omni-commerce-ai

docker compose exec backend python scripts/seed_auth_accounts.py
```

默认 demo 账号：

| username | password    | role     | user_no |
|----------|-------------|----------|---------|
| admin    | admin123    | admin    | U100001 |
| operator | operator123 | operator | U100001 |
| viewer   | viewer123   | viewer   | U200001 |

这些账号仅用于本地开发、测试和演示。生产环境必须通过环境变量或安全初始化流程设置密码，不得复用 demo 密码。

## 11. 测试方式

默认测试必须使用 mock，不依赖真实模型 API。

~~~powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/ -q
~~~

### 11.1 Auth / RBAC 测试

默认兼容模式：

```powershell
cd D:\omni-commerce-ai\backend

$env:AUTH_ENABLED="false"
$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/ -q
```

当前结果：

```text
130 passed, 4 skipped, 1 warning
```

其中 `tests/test_rbac_api.py` 需要 backend 以 `AUTH_ENABLED=true` 启动，因此在默认兼容模式下会被跳过。

认证 / RBAC 专项测试：

```powershell
python -m pytest tests/test_auth_service.py tests/test_auth_api.py tests/test_rbac_dependencies.py -q
```

当前结果：

```text
13 passed
```

生产化认证模式 API 级 RBAC 验证：

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

然后执行：

```powershell
cd D:\omni-commerce-ai\backend

$env:AUTH_ENABLED="true"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/test_rbac_api.py -q
```

当前结果：

```text
4 passed
```

测试完成后恢复兼容模式：

```powershell
cd D:\omni-commerce-ai

$env:AUTH_ENABLED="false"
docker compose up -d --build backend
```

当前窗口 12 接手时已验证：

~~~text
117 passed, 1 warning
~~~

其中 warning 为既有 asyncpg 资源释放 warning，不阻塞当前业务链路。

## 12. 真实模型 Smoke Test

真实模型 smoke test 不纳入默认 pytest。默认开发和自动化测试继续使用 mock：

~~~env
DEFAULT_LLM_PROVIDER=mock
DEFAULT_LLM_MODEL=mock-chat-model
DEFAULT_EMBEDDING_PROVIDER=mock
DEFAULT_EMBEDDING_MODEL=mock-embedding-model
~~~

真实模型 smoke test 前，backend 容器必须注入：

~~~env
DEFAULT_LLM_PROVIDER=openai_compatible
DEFAULT_LLM_MODEL=qwen-turbo
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=用户本地自己的 API Key
~~~

安全要求：

- 不要把真实 API Key 写进代码
- 不要把真实 API Key 写进 README
- 不要把真实 API Key 写进测试文件
- 不要把真实 API Key 写进交接文档
- 只能通过本地 `.env` 或临时环境变量注入
- `.env` 必须在 `.gitignore` 中

重启 backend：

~~~powershell
cd D:\omni-commerce-ai
docker compose up -d --build backend
~~~

执行 smoke test 前，先验证容器环境变量。注意不要打印真实 Key：

~~~powershell
docker compose exec backend sh -lc "env | grep -E 'DEFAULT_LLM|LLM_BASE_URL|LLM_API_KEY|REAL_LLM' | sed -E 's#^(LLM_API_KEY=).*#\1***MASKED***#'"
~~~

如果看到：

~~~text
DEFAULT_LLM_PROVIDER=mock
~~~

说明业务链路仍会走 mock，不要继续声明真实模型业务链路通过。

还需要确认 active Prompt 的 `model_config_json`。因为 RAG、客服政策问答、内容生成等业务链路会优先使用 Prompt 版本中的模型配置：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select pt.scene, pt.template_key, pv.version, pv.is_active, pv.status, pv.model_config_json from prompt_template pt join prompt_version pv on pv.template_id = pt.id where pt.tenant_id = '00000000-0000-0000-0000-000000000001' and pt.deleted_at is null and pv.deleted_at is null and pv.is_active = true and pv.status = 'active' and pt.scene in ('rag_answer_generation','customer_service_intent','customer_service_answer','content_generation') order by pt.scene, pt.template_key;"
~~~

真实模型 smoke test 要验证完整业务链路时，需要临时将相关 active Prompt 的 `model_config_json` 切到：

~~~json
{
  "provider": "openai_compatible",
  "model": "qwen-turbo"
}
~~~

执行 smoke test：

~~~powershell
cd D:\omni-commerce-ai\backend
python scripts/smoke_test_real_llm.py
~~~

脚本会检查：

- `/api/v1/llm/chat` 是否返回 `provider=openai_compatible`
- `/api/v1/llm/chat` 是否返回 `model_name=qwen-turbo`
- `/api/v1/knowledge/ask` 的 answer 是否仍以 `[mock]` 开头
- `/api/v1/agents/customer-service/chat` 的政策问答 answer 是否仍以 `[mock]` 开头
- `/api/v1/content/generate/product-title` 的生成内容是否仍以 `[mock]` 开头

如果检测到 `[mock]`，说明业务链路尚未完全切到真实模型。应检查 backend 容器环境变量和 Prompt 版本 `model_config_json`
是否仍配置为 mock。

smoke test 后建议查询模型调用日志：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select provider, model_name, call_type, status, latency_ms, input_tokens, output_tokens, total_tokens, created_at from model_call_log order by created_at desc limit 20;"
~~~

完整通过时，应能看到多条：

~~~text
openai_compatible | qwen-turbo | chat | success
~~~

真实模型 smoke test 完成后，必须恢复默认 mock Prompt 配置和 backend 环境，保证默认 pytest 不依赖真实模型。

## 13. 可观测性与日志查询

详见：

~~~text
docs/observability_guide.md
~~~

重点表：

- `model_call_log`
- `rag_retrieval_log`
- `agent_task`
- `agent_step_log`
- `tool_call_log`
- `evaluation_result`
- `content_asset`
- `content_review`

## 14. 演示脚本

详见：

~~~text
docs/demo_script.md
~~~

覆盖：

1. 商品查询
2. RAG 问答
3. 客服 Agent 查订单
4. 客服 Agent 投诉转人工
5. 导购 Agent 预算推荐
6. 运营 Copilot 查询 GMV
7. 内容生成与审核
8. 评测中心执行与查询

## 15. 已知边界

- 认证 / RBAC / 租户隔离已完成轻量生产化增强，但仍保留 `AUTH_ENABLED=false` 兼容模式，便于旧测试和旧演示继续运行。
- 当前仍保留部分接口显式传入 `tenant_id` 的 API 合同；在 `AUTH_ENABLED=true` 时，系统会优先使用 JWT 中的 `tenant_id`
  ，并校验请求 `tenant_id` 与 token `tenant_id` 是否一致。
- Agent 对话类接口暂未强制接入认证，主要是为了避免破坏 v1.0 已通过的客服、导购、运营 Copilot 演示主链路。
- 默认测试使用 mock 模型，真实模型只用于 smoke test
- `conversion_rate` 已注册但不硬算，因为缺少曝光、访问、点击、加购行为数据
- Reranker 当前为 NoopReranker
- OpenSearch 中文分词可进一步增强
- 内容生成当前不做真实发布，只做到 approved 可发布状态
- 全量测试存在一个既有 asyncpg warning，不影响当前测试通过

## 16. 后续优化

- 在现有轻量 Auth / RBAC 基础上，继续扩展更细粒度的企业权限能力，例如组织架构、菜单权限、SSO / OAuth2、字段级权限等。
- 新增 evaluation_run 批次表
- 接入 Ragas / LLM-as-judge
- 接入真实 reranker
- 增加行为埋点表，完善转化率指标
- 接入 Prometheus / Grafana / OpenTelemetry
- 增强测试隔离和异步连接生命周期管理
