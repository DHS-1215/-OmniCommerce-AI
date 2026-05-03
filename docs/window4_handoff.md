# 模块交接文档：执行窗口 4 - 模型网关

## 一、模块目标

本模块负责建立《智营 OmniCommerce AI》统一模型调用入口，为后续 Prompt 管理、RAG、Agent、评测中心等模块提供统一的 LLM /
Embedding / Stream 调用能力。

本窗口核心目标：

```text
所有模型调用必须统一经过 backend/app/llm/
禁止业务 service、Agent、RAG、Prompt 模块直接调用外部模型 API
```

本窗口不实现：

- Prompt CRUD；
- Prompt 变量渲染；
- RAG；
- Agent；
- 业务 API 修改；
- 数据库表结构修改。

---

## 二、窗口识别结果

| 项目                          | 内容                          |
|-----------------------------|-----------------------------|
| 当前执行窗口                      | 执行窗口 4                      |
| 当前窗口名称                      | 模型网关                        |
| 本窗口目标                       | 建立统一模型调用入口                  |
| 上游依赖                        | 执行窗口 1：基础工程骨架；执行窗口 2：核心数据模型 |
| 参考依赖                        | 执行窗口 3：基础业务服务               |
| 是否修改数据库结构                   | 否                           |
| 是否新增 Alembic 迁移             | 否                           |
| 是否越权实现 Prompt / RAG / Agent | 否                           |

---

## 三、已完成内容

本窗口已完成：

- LLM 统一调用接口；
- Embedding 统一调用接口；
- SSE 流式输出接口；
- 模型 Provider 抽象基类；
- 正式 Mock Provider；
- OpenAI-compatible Provider；
- 模型 Provider Router；
- Chat / Embedding 默认 Provider 分离；
- 失败重试机制；
- 错误归一化；
- 模型调用日志入库；
- Token 统计字段写入；
- 成本统计字段预留；
- `retry_count` 日志记录；
- API 测试入口；
- 自动化测试。

本窗口未实现：

- Prompt CRUD；
- Prompt 变量渲染；
- RAG 检索链路；
- Agent 编排；
- 真实业务 service 调用模型；
- 数据库表结构调整。

---

## 四、新增文件清单

```text
backend/app/llm/__init__.py
backend/app/llm/base.py
backend/app/llm/schemas.py
backend/app/llm/router.py
backend/app/llm/gateway.py
backend/app/llm/providers/__init__.py
backend/app/llm/providers/mock.py
backend/app/llm/providers/openai_compatible.py
backend/app/services/model_call_log_service.py
backend/app/api/v1/llm.py
backend/tests/test_llm_gateway.py
backend/tests/test_llm_api.py
```

---

## 五、修改文件清单

```text
backend/app/core/config.py
backend/app/core/exceptions.py
backend/app/api/v1/router.py
backend/.env.example
backend/pyproject.toml
```

---

### 5.1 `backend/app/core/config.py`

新增模型网关配置：

```text
DEFAULT_LLM_PROVIDER
DEFAULT_EMBEDDING_PROVIDER
DEFAULT_LLM_MODEL
DEFAULT_EMBEDDING_MODEL
LLM_BASE_URL
LLM_API_KEY
LLM_TIMEOUT_SECONDS
LLM_MAX_RETRIES
```

---

### 5.2 `backend/app/core/exceptions.py`

增强 `ModelGatewayException`，支持：

- 自定义错误码；
- 错误 `data`；
- `retry_count` 传递；
- 统一 `502` 网关错误响应。

---

### 5.3 `backend/app/api/v1/router.py`

新增模型网关路由注册：

```text
/api/v1/llm
```

---

### 5.4 `backend/.env.example`

新增模型网关环境变量示例。

默认使用：

```text
mock
```

不要求真实 API Key。

---

### 5.5 `backend/pyproject.toml`

将 `httpx` 移入正式 dependencies。

原因：

> 模型网关运行时需要 HTTP 客户端能力。

---

## 六、数据库变更

### 6.1 新增数据表

无。

### 6.2 修改数据表

无。

### 6.3 Alembic 迁移

无新增 migration。

---

### 6.4 使用现有表

本窗口复用执行窗口 2 已创建的表：

```text
model_call_log
```

写入字段包括：

```text
tenant_id
request_id
user_id
provider
model_name
model_type
call_type
prompt_template_id
prompt_version_id
input_tokens
output_tokens
total_tokens
cost_amount
currency
latency_ms
status
error_code
error_message
input_summary
output_summary
metadata_json
```

---

## 七、API 接口清单

## 7.1 接口 1：普通 Chat 调用

| 项目       | 内容                              |
|----------|---------------------------------|
| 方法       | `POST`                          |
| 路径       | `/api/v1/llm/chat`              |
| 响应格式     | 统一 JSON 响应                      |
| Provider | 支持 `mock` / `openai_compatible` |
| 是否写日志    | 是                               |

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "provider": "mock",
  "model": "mock-chat-model",
  "messages": [
    {
      "role": "user",
      "content": "你好，模型网关"
    }
  ]
}
```

验证结果：

```text
success = true
provider = mock
model_name = mock-chat-model
content = [mock] 你好，模型网关
request_id 已返回
model_call_log 已写入
```

---

## 7.2 接口 2：Embedding 调用

| 项目       | 内容                              |
|----------|---------------------------------|
| 方法       | `POST`                          |
| 路径       | `/api/v1/llm/embeddings`        |
| 响应格式     | 统一 JSON 响应                      |
| Provider | 支持 `mock` / `openai_compatible` |
| 是否写日志    | 是                               |

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "provider": "mock",
  "model": "mock-embedding-model",
  "texts": [
    "智能客服",
    "企业知识库 RAG"
  ]
}
```

验证结果：

```text
success = true
provider = mock
model_name = mock-embedding-model
embeddings 返回 2 条
request_id 已返回
model_call_log 已写入
```

---

## 7.3 接口 3：SSE 流式 Chat 调用

| 项目                  | 内容                        |
|---------------------|---------------------------|
| 方法                  | `POST`                    |
| 路径                  | `/api/v1/llm/chat/stream` |
| 响应格式                | `text/event-stream`       |
| 是否统一 JSON 包裹        | 否                         |
| 是否返回 `X-Request-ID` | 是                         |
| 是否写日志               | 是                         |

说明：

> 该接口是 SSE 协议特例。  
> SSE 必须持续返回 `data: xxx` 格式事件流，因此不走普通 JSON 包裹。  
> 但接口仍返回 `X-Request-ID`，满足请求追踪要求。

验证结果：

```text
data: {"content": "[mock]"}

data: {"content": " stream"}

data: {"content": " response"}

data: [DONE]
```

---

## 八、配置项说明

### 8.1 默认 Mock 配置

```env
# Model Gateway
DEFAULT_LLM_PROVIDER=mock
DEFAULT_EMBEDDING_PROVIDER=mock
DEFAULT_LLM_MODEL=mock-chat-model
DEFAULT_EMBEDDING_MODEL=mock-embedding-model

LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=

LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

---

### 8.2 真实模型调用配置示例

```env
DEFAULT_LLM_PROVIDER=openai_compatible
DEFAULT_EMBEDDING_PROVIDER=openai_compatible
DEFAULT_LLM_MODEL=qwen-plus
DEFAULT_EMBEDDING_MODEL=text-embedding-v3

LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=真实 API Key
```

注意：

```text
LLM_API_KEY 不得写入 .env.example
真实 Key 只能放本地 .env 或部署环境变量
```

---

## 九、运行方式

### 9.1 启动服务

```bash
cd D:\omni-commerce-ai
docker compose up -d --build
```

### 9.2 查看服务状态

```bash
docker compose ps
```

### 9.3 健康检查

```bash
curl.exe "http://127.0.0.1:8002/api/v1/health"
```

---

## 十、测试方式

### 10.1 宿主机模型网关测试

```bash
cd D:\omni-commerce-ai\backend
python -m pytest tests/test_llm_gateway.py tests/test_llm_api.py
```

已验证结果：

```text
9 passed
```

---

### 10.2 容器内全量测试

```bash
cd D:\omni-commerce-ai
docker compose exec backend python -m pytest tests/
```

已验证结果：

```text
42 passed in 3.70s
```

测试覆盖：

- 窗口 1 基础测试；
- 窗口 3 业务 API 测试；
- 窗口 4 模型网关核心测试；
- 窗口 4 模型网关 API 测试。

---

## 十一、模型调用日志验证

执行命令：

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select provider, model_name, model_type, call_type, status, input_tokens, output_tokens, total_tokens, latency_ms, error_code, metadata_json, created_at from model_call_log order by created_at desc limit 10;"
```

已验证入库记录：

```text
mock | mock-chat-model      | llm       | stream_chat | success
mock | mock-embedding-model | embedding | embedding   | success
mock | mock-chat-model      | llm       | chat        | success
```

`metadata_json` 已记录：

```json
{
  "retry_count": 0
}
```

SSE 日志已记录：

```json
{
  "stream": true,
  "chunk_count": 3,
  "retry_count": 0
}
```

---

## 十二、局部实现决策

### 决策 1：新增正式 Mock Provider

| 项目      | 内容                                     |
|---------|----------------------------------------|
| 决策内容    | 新增 `backend/app/llm/providers/mock.py` |
| 决策原因    | 保证本地开发和自动化测试不依赖真实模型 API Key            |
| 影响范围    | 模型网关测试、后续 Agent / RAG 测试               |
| 后续可调整方式 | Mock 输出可按后续场景扩展，但不应替代真实 Provider       |

---

### 决策 2：Chat 和 Embedding 默认 Provider 分离

| 项目      | 内容                                                  |
|---------|-----------------------------------------------------|
| 决策内容    | `DEFAULT_LLM_PROVIDER`、`DEFAULT_EMBEDDING_PROVIDER` |
| 决策原因    | 实际项目中 Chat 模型和 Embedding 模型可能来自不同供应商                |
| 影响范围    | 模型路由、配置项、后续 RAG 向量化                                 |
| 后续可调整方式 | 后续可扩展为按租户、按场景、按成本路由                                 |

---

### 决策 3：OpenAI-compatible Provider 使用 `httpx` 直连

| 项目      | 内容                                                 |
|---------|----------------------------------------------------|
| 决策内容    | 不引入 OpenAI SDK，直接使用 `httpx`                        |
| 决策原因    | 降低 SDK 绑定，增强对百炼、DeepSeek、OpenRouter、硅基流动等兼容接口的适配能力 |
| 影响范围    | 模型 Provider 实现                                     |
| 后续可调整方式 | 如后续需要官方 SDK 能力，可新增独立 Provider，不替换当前抽象              |

---

### 决策 4：失败重试只覆盖普通 Chat / Embedding

| 项目      | 内容                                                                                              |
|---------|-------------------------------------------------------------------------------------------------|
| 决策内容    | `timeout` 可重试；network error 可重试；`5xx` 可重试；`400 / 401 / 403` 不重试；最终失败统一抛 `ModelGatewayException` |
| 决策原因    | 符合外部模型调用常见故障处理逻辑                                                                                |
| 影响范围    | OpenAI-compatible Provider                                                                      |
| 后续可调整方式 | 可扩展指数退避、熔断、Provider fallback                                                                    |

---

### 决策 5：SSE 流式接口不做中途重试

| 项目      | 内容                                           |
|---------|----------------------------------------------|
| 决策内容    | `/api/v1/llm/chat/stream` 连接失败时归一化错误，但不做中途重试 |
| 决策原因    | 流式接口一旦部分内容已输出，中途重试可能造成重复输出                   |
| 影响范围    | SSE 流式调用                                     |
| 后续可调整方式 | 后续可在前端或 Agent 层设计断线重连协议                      |

---

### 决策 6：日志只保存摘要，不保存完整 Prompt / 输出

| 项目      | 内容                                         |
|---------|--------------------------------------------|
| 决策内容    | `input_summary` 截断保存；`output_summary` 截断保存 |
| 决策原因    | 避免敏感信息、超长文本、隐私数据进入日志表                      |
| 影响范围    | `model_call_log`                           |
| 后续可调整方式 | 可接入脱敏策略、审计策略、对象存储归档                        |

---

### 决策 7：SSE 接口作为协议特例

| 项目      | 内容                                               |
|---------|--------------------------------------------------|
| 决策内容    | `/api/v1/llm/chat/stream` 返回 `text/event-stream` |
| 决策原因    | SSE 协议要求持续返回事件流，不能普通 JSON 包裹                     |
| 影响范围    | API 响应格式                                         |
| 后续可调整方式 | 前端和 API 文档中明确标注该接口为协议特例                          |

---

## 十三、已知问题

当前已知问题如下：

1. 当前 `openai_compatible` Provider 已实现普通 Chat / Embedding 的失败重试，但尚未接入真实成本计算；
2. 当前 Token 成本字段 `cost_amount` / `currency` 预留，暂未根据模型价格自动计算；
3. 当前模型路由只支持 provider name 路由，尚未支持租户级、场景级、成本级、故障降级路由；
4. 当前 SSE 流式接口不做中途重试，避免重复输出；
5. 当前 Mock Provider 输出固定规则，仅用于测试和开发，不代表真实模型能力；
6. 当前日志摘要只做长度截断，尚未做复杂脱敏；
7. 当前未接入 Prompt 管理，`prompt_template_id` / `prompt_version_id` 仅作为日志字段透传预留。

---

## 十四、需总控确认事项

暂无阻塞事项。

已按总控裁决完成：

- Mock Provider：已完成；
- router 注册 `mock` 和 `openai_compatible`：已完成；
- 自动化测试默认使用 `mock`：已完成；
- 失败重试：已完成；
- `DEFAULT_EMBEDDING_PROVIDER`：已完成；
- SSE 协议特例：已完成；
- `httpx` 移入正式 dependencies：已完成；
- `test_llm_api.py`：已完成。

SSE 协议特例已在代码注释和本交接文档中说明。

---

## 十五、给下一个执行窗口的注意事项

后续窗口接手时请注意：

1. 后续 Prompt 管理模块不得直接调用模型 API，必须通过 `ModelGateway`；
2. 后续 RAG 模块做 Embedding 时必须通过 `ModelGateway.embeddings()`；
3. 后续 Agent 模块做 Chat / Stream 时必须通过 `ModelGateway.chat()` 或 `ModelGateway.stream_chat()`；
4. 后续如果要接入新供应商，只新增 Provider 实现，不要改业务 service；
5. 后续如果要按租户切模型，应扩展 `ModelProviderRouter`，不要绕开网关；
6. 后续如果要统计成本，应在模型网关层统一计算并写入 `model_call_log.cost_amount`；
7. 后续如果要保存完整 Prompt / 输出，必须先经过总控确认隐私和审计策略。

---

## 十六、本窗口交付结论

| 项目         | 结果               |
|------------|------------------|
| 自评状态       | 已完成              |
| 是否建议进入下一窗口 | 是                |
| 建议进入       | 执行窗口 5：Prompt 管理 |

原因说明：

- 已建立统一模型调用入口；
- 已完成 LLM / Embedding / SSE 三类调用能力；
- 已完成 Mock Provider 和 OpenAI-compatible Provider；
- 已完成失败重试与错误归一化；
- 已完成模型调用日志入库；
- 已完成 API 测试入口；
- 自动化测试通过，容器内全量测试结果为 `42 passed in 3.70s`；
- 未越权实现 Prompt / RAG / Agent；
- 未修改业务 API；
- 未修改数据库表结构。

---

## 十七、一句话交接总结

执行窗口 4 已完成智营 OmniCommerce AI 的模型网关建设，建立了统一 LLM / Embedding / Stream 调用入口。

后续所有 Prompt、RAG、Agent、评测相关模型调用都必须走：

```text
backend/app/llm/
ModelGateway
```

不能绕过模型网关直接调用外部模型 API。