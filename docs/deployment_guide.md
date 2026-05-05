# 部署与启动说明

本文档用于说明智营 OmniCommerce AI 的本地部署、端口、环境变量、数据库迁移、种子数据和测试方式。

## 1. 一键启动

项目根目录执行：

~~~powershell
cd D:\omni-commerce-ai
docker compose up -d --build
~~~

查看服务状态：

~~~powershell
docker compose ps
~~~

后端健康检查：

~~~powershell
curl.exe "http://127.0.0.1:8002/api/v1/health"
~~~

预期核心字段：

~~~text
success = true
data.status = ok
data.database = ok
data.redis = ok
request_id = req_xxx
~~~

## 2. 端口说明

| 服务                     | 宿主机访问          | 容器内部            |
|------------------------|----------------|-----------------|
| Backend                | 127.0.0.1:8002 | backend:8000    |
| PostgreSQL             | 127.0.0.1:5432 | postgres:5432   |
| MinIO S3 API           | 127.0.0.1:9000 | minio:9000      |
| MinIO Console          | 127.0.0.1:9001 | minio:9001      |
| OpenSearch             | 127.0.0.1:9200 | opensearch:9200 |
| OpenSearch Performance | 127.0.0.1:9600 | opensearch:9600 |
| Qdrant                 | 容器内访问为主        | qdrant:6333     |
| Redis                  | 容器内访问为主        | redis:6379      |

重点说明：

~~~text
宿主机后端访问地址是：http://127.0.0.1:8002
容器内部 Uvicorn 地址是：0.0.0.0:8000
Docker Compose 映射关系是：8002 -> 8000
~~~

如果测试打到 `127.0.0.1:8000`，可能出现大量 404。这不是业务接口失败，而是端口打错。

## 3. 基础环境变量

默认开发和测试使用 mock 模型，不依赖真实大模型 API Key。

### 3.x Auth / JWT 环境变量

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
- `backend/.env` 不进入 Git，只提交 `backend/.env.example`；
- Docker Compose 已支持从宿主机注入 `AUTH_ENABLED`、`JWT_SECRET_KEY`、`JWT_ALGORITHM`、`JWT_EXPIRE_MINUTES`。

~~~env
DEFAULT_LLM_PROVIDER=mock
DEFAULT_LLM_MODEL=mock-chat-model
DEFAULT_EMBEDDING_PROVIDER=mock
DEFAULT_EMBEDDING_MODEL=mock-embedding-model
~~~

数据库和 Redis：

~~~env
DATABASE_URL=postgresql+asyncpg://omni:omni_password@postgres:5432/omni_ai
REDIS_URL=redis://redis:6379/0
~~~

RAG 相关：

~~~env
RAG_VECTOR_COLLECTION=omni_knowledge_chunks
RAG_VECTOR_SIZE=3
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=80
RAG_TOP_K=5
RAG_VECTOR_WEIGHT=0.65
RAG_KEYWORD_WEIGHT=0.35
RAG_RERANK_TOP_N=5
~~~

OpenSearch：

~~~env
OPENSEARCH_URL=http://opensearch:9200
OPENSEARCH_INDEX=omni_knowledge_chunks
OPENSEARCH_USERNAME=
OPENSEARCH_PASSWORD=
~~~

MinIO：

~~~env
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=omni_minio
MINIO_SECRET_KEY=omni_minio_password
MINIO_BUCKET_KNOWLEDGE=omni-knowledge
MINIO_SECURE=false
~~~

## 4. 真实模型配置

真实模型只用于 smoke test 或人工演示，不进入默认 pytest。

示例：

~~~powershell
$env:DEFAULT_LLM_PROVIDER="openai_compatible"
$env:DEFAULT_LLM_MODEL="qwen-turbo"
$env:DEFAULT_EMBEDDING_PROVIDER="openai_compatible"
$env:DEFAULT_EMBEDDING_MODEL="text-embedding-v3"
$env:LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:LLM_API_KEY="用户本地自己的 API Key"
~~~

安全要求：

- 不要把真实 API Key 写进代码
- 不要把真实 API Key 写进 README
- 不要把真实 API Key 写进测试文件
- 不要提交本地 `.env`
- 默认 pytest 继续使用 mock provider

如果通过 Docker Compose 运行后端，需要让 backend 容器读取到这些环境变量，并重启 backend。

## 5. 数据库迁移

进入后端目录：

~~~powershell
cd D:\omni-commerce-ai\backend
python -m alembic current
python -m alembic upgrade head
~~~

窗口 12 接手时当前数据库版本：

~~~text
d62c219e9482 (head)
~~~

该版本包含内容生成与审核流相关表：

~~~text
content_asset
content_review
~~~

## 6. 种子数据

进入后端目录：

~~~powershell
cd D:\omni-commerce-ai\backend
~~~

初始化核心验证数据：

~~~powershell
python scripts/seed_core_data.py
~~~

初始化 Demo 场景数据：

~~~powershell
python scripts/seed_demo_scenarios.py
~~~

初始化默认 Prompt：

~~~powershell
python scripts/seed_prompt_data.py
~~~

种子数据覆盖：

- 用户画像
- 商品 / SKU / 评价
- 订单 / 售后 / 工单
- 知识库基础数据
- Prompt 默认模板

### 认证账号种子数据

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

## 7. 测试方式

测试前必须设置后端地址为宿主机端口 8002。

~~~powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/ -q
~~~

窗口 12 接手时已验证：

~~~text
117 passed, 1 warning
~~~

其中 warning 为既有 asyncpg 资源释放 warning，不阻塞当前主业务链路。

## 8. 真实模型 Smoke Test

真实模型 smoke test 不纳入默认 pytest。

默认开发和测试使用：

~~~env
DEFAULT_LLM_PROVIDER=mock
DEFAULT_LLM_MODEL=mock-chat-model
~~~

真实模型 smoke test 前，backend 容器必须切换为：

~~~env
DEFAULT_LLM_PROVIDER=openai_compatible
DEFAULT_LLM_MODEL=qwen-turbo
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=用户本地自己的 API Key
~~~

不要把真实 API Key 写进代码、README、测试文件或交接文档。只能通过本地 `.env` 或临时环境变量注入，且 `.env`
必须在 `.gitignore` 中。

重启 backend：

~~~powershell
cd D:\omni-commerce-ai
docker compose up -d --build backend
~~~

验证容器环境变量。不要打印真实 Key：

~~~powershell
docker compose exec backend sh -lc "env | grep -E 'DEFAULT_LLM|LLM_BASE_URL|LLM_API_KEY|REAL_LLM' | sed -E 's#^(LLM_API_KEY=).*#\1***MASKED***#'"
~~~

如果 `DEFAULT_LLM_PROVIDER=mock`，则业务链路仍会走 mock。

还需要检查 active Prompt 的模型配置：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select pt.scene, pt.template_key, pv.version, pv.is_active, pv.status, pv.model_config_json from prompt_template pt join prompt_version pv on pv.template_id = pt.id where pt.tenant_id = '00000000-0000-0000-0000-000000000001' and pt.deleted_at is null and pv.deleted_at is null and pv.is_active = true and pv.status = 'active' and pt.scene in ('rag_answer_generation','customer_service_intent','customer_service_answer','content_generation') order by pt.scene, pt.template_key;"
~~~

注意：业务链路会优先使用 Prompt 版本中的 `model_config_json`。如果这里仍是：

~~~json
{
  "provider": "mock",
  "model": "mock-chat-model"
}
~~~

那么 RAG、客服政策问答、内容生成仍会走 mock，即使 backend 容器的 `DEFAULT_LLM_PROVIDER` 已经是 `openai_compatible`。

执行 smoke test：

~~~powershell
cd D:\omni-commerce-ai\backend
python scripts/smoke_test_real_llm.py
~~~

脚本不只判断 HTTP 200 和 `success=true`，还会检查关键业务链路返回内容是否仍以 `[mock]` 开头。

smoke test 后建议查询模型调用日志：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select provider, model_name, call_type, status, latency_ms, input_tokens, output_tokens, total_tokens, created_at from model_call_log order by created_at desc limit 20;"
~~~

预期能看到多条：

~~~text
openai_compatible | qwen-turbo | chat | success
~~~

如果只有 `/api/v1/llm/chat` 一条是 `openai_compatible`，而 RAG / 内容生成 / 客服政策问答仍是 `mock`，说明业务链路尚未完全切到真实模型，需要检查
Prompt 版本 `model_config_json`。

真实模型 smoke test 完成后，应恢复 Prompt 配置为 mock，并恢复 backend 默认 mock 环境，保证默认 pytest 仍然稳定。

### Auth / RBAC 测试

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

## 9. 选购指南知识库样例

窗口 12 新增样例目录：

~~~text
docs/sample_knowledge/
~~~

建议样例文件：

~~~text
shopping_guide_office_appliance.md
shopping_guide_electric_kettle.md
shopping_guide_bluetooth_headphone.md
shopping_guide_material_safety.md
~~~

上传示例：

~~~powershell
cd D:\omni-commerce-ai

curl.exe -X POST "http://127.0.0.1:8002/api/v1/knowledge/documents/upload" `
  -F "tenant_id=00000000-0000-0000-0000-000000000001" `
  -F "title=办公室小家电选购指南" `
  -F "language=zh-CN" `
  -F "file=@docs/sample_knowledge/shopping_guide_office_appliance.md"
~~~

上传后会触发：

~~~text
MinIO 保存原始文件
Parser 解析
Chunk 切片
PostgreSQL 写入 knowledge_document / knowledge_chunk
Embedding
Qdrant 入库
OpenSearch 索引
document.status = indexed
~~~

## 10. 常用健康检查

后端：

~~~powershell
curl.exe "http://127.0.0.1:8002/api/v1/health"
~~~

OpenSearch：

~~~powershell
curl.exe "http://127.0.0.1:9200"
curl.exe "http://127.0.0.1:9200/_cluster/health"
curl.exe "http://127.0.0.1:9200/_cat/indices?v"
~~~

MinIO：

~~~powershell
curl.exe "http://127.0.0.1:9000/minio/health/live"
~~~

Alembic：

~~~powershell
cd D:\omni-commerce-ai\backend
python -m alembic current
~~~

## 11. 常见问题

### 11.1 测试大量 404

优先检查测试地址：

~~~text
错误：127.0.0.1:8000
正确：127.0.0.1:8002
~~~

### 11.2 真实模型 smoke test 失败

检查：

- `LLM_API_KEY` 是否在 backend 运行环境中
- `LLM_BASE_URL` 是否正确
- 模型名是否可用
- 额度是否充足
- backend 是否重启
- 默认 mock pytest 不受影响

### AUTH_ENABLED 配置未生效

现象：

- 本地 PowerShell 设置了 `$env:AUTH_ENABLED="true"`；
- 但接口仍然没有触发 RBAC；
- `tests/test_rbac_api.py` 返回 404，而不是预期的 403。

排查：

```powershell
cd D:\omni-commerce-ai

docker compose exec backend python -c "from app.core.config import get_settings; s=get_settings(); print('AUTH_ENABLED=', s.auth_enabled)"
```

如果输出：

```text
AUTH_ENABLED= False
```

说明 backend 容器没有读到宿主机环境变量。需要确认 `docker-compose.yml` 中 backend environment 是否包含：

```yaml
AUTH_ENABLED: ${AUTH_ENABLED:-false}
JWT_SECRET_KEY: ${JWT_SECRET_KEY:-change_me_in_local_env}
JWT_ALGORITHM: ${JWT_ALGORITHM:-HS256}
JWT_EXPIRE_MINUTES: ${JWT_EXPIRE_MINUTES:-1440}
```

修改后重启 backend：

```powershell
$env:AUTH_ENABLED="true"
docker compose up -d --build backend
```

再次确认容器内配置为：

```text
AUTH_ENABLED= True
```

### 11.3 asyncpg warning

当前存在：

~~~text
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
~~~

当前判断：

- 全量测试通过
- 健康检查通过
- 主业务链路可演示
- 不建议为了压 warning 大改业务代码

后续可以小范围排查：

- pytest fixture
- httpx 调用方式
- SQLAlchemy AsyncSession 生命周期
- asyncpg 连接池关闭时机

### 11.4 OpenSearch 中文检索效果一般

当前使用默认 analyzer。后续可接：

- IK Analyzer
- 中文分词 analyzer
- 更细的字段 mapping

### 11.5 切换真实 Embedding 后 RAG 失败

当前 mock embedding 维度为 3：

~~~env
RAG_VECTOR_SIZE=3
~~~

如果切换真实 embedding 模型，需要同步调整：

- `RAG_VECTOR_SIZE`
- Qdrant collection
- 已有向量数据重建

### 11.6 MinIO 与 PostgreSQL 不是强事务

当前策略是 best-effort cleanup。后续可增强：

- outbox 事件表
- 孤儿对象清理任务
- 对象状态字段
