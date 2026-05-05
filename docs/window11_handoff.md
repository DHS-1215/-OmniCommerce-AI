# 模块交接文档：执行窗口 11 - 评测中心

## 一、模块目标

本模块负责建立《智营 OmniCommerce AI：电商企业级大模型运营中台》的评测中心能力，为
RAG、Agent、Prompt、工具调用、检索策略等大模型应用链路提供可创建、可执行、可入库、可查询、可对比的评测体系。

本窗口不是简单打印“效果不错”，而是将评测用例、评测执行、指标计算、结果入库和报告查询形成正式闭环。

本窗口服务于项目中的评测与优化层，支撑后续：

- RAG 回答质量评估；
- Agent 任务成功率评估；
- 工具调用成功率评估；
- Prompt 版本效果对比；
- 检索策略效果对比；
- 面试中解释“如何评估大模型应用效果”。

---

## 二、窗口识别结果

| 项目     | 内容                            |
|--------|-------------------------------|
| 当前执行窗口 | 执行窗口 11                       |
| 当前窗口名称 | 评测中心                          |
| 本窗口目标  | 建立 RAG、Agent、Prompt、工具调用的评测体系 |

---

### 2.1 本窗口必须完成

- RAG 评测用例管理；
- Agent 评测用例管理；
- 答案相关性评估；
- 忠实度评估；
- 上下文召回评估；
- 工具调用成功率统计；
- Agent 成功率统计；
- Prompt 版本对比；
- 检索策略对比；
- 评测结果入库；
- 评测报告接口。

---

### 2.2 本窗口禁止完成

- 只在控制台打印评测结果；
- 只写主观“效果不错”；
- 绕过 `evaluation_result` 表；
- 绕过 RAG / Agent / Prompt / ModelGateway 已有链路；
- 越权实现窗口 12 可观测性部署。

---

### 2.3 上游依赖

- 执行窗口 1：基础工程骨架；
- 执行窗口 2：核心数据模型；
- 执行窗口 4：模型网关；
- 执行窗口 5：Prompt 管理；
- 执行窗口 6：企业知识库 RAG；
- 执行窗口 7：智能客服 Agent；
- 执行窗口 8 / 9 / 10：作为增强参考。

---

### 2.4 最终交付物

- 评测用例 API；
- RAG 评测执行器；
- Agent 评测执行器；
- 自定义评测指标计算器；
- 评测结果入库服务；
- 评测报告接口；
- Prompt 版本对比接口；
- 检索策略对比接口；
- 自动化测试；
- 模块交接文档。

---

### 2.5 验收标准

- 可创建评测用例；
- 可执行 RAG 评测；
- 可执行 Agent 评测；
- 评测结果可入库；
- 可查看评测报告；
- 可对比 Prompt 或检索策略；
- 全量测试通过；
- 不引入 Java / Spring 技术栈。

---

## 三、已完成内容

本窗口已完成：

1. 新增评测中心 API 路由：

```http
/api/v1/evaluations
```

2. 新增评测用例管理能力：

- 创建评测用例；
- 查询评测用例列表；
- 查询评测用例详情；
- 更新评测用例；
- 归档评测用例。

3. 新增 RAG 评测执行能力：

- 从 `evaluation_case.input_json` 读取问题；
- 调用 `KnowledgeService.ask()`；
- 获取 RAG 回答和 citations；
- 计算答案相关性、忠实度、上下文召回、上下文精确率；
- 将结果写入 `evaluation_result`。

4. 新增 Agent 评测执行能力：

- 支持 `customer_service`；
- 支持 `shopping_guide`；
- 支持 `operation_copilot`；
- 根据 Agent 类型调用对应 Agent Service；
- 计算工具调用成功率和 Agent 任务成功率；
- 将结果写入 `evaluation_result`。

5. 新增评测指标计算模块：

```text
answer_relevance
faithfulness
context_recall
context_precision
tool_call_success_rate
agent_task_success_rate
score
```

6. 新增评测结果查询接口；
7. 新增评测报告接口；
8. 新增 Prompt 版本对比接口；
9. 新增检索策略对比接口；
10. 新增自动化测试：

```text
test_evaluation_metrics.py
test_evaluation_api.py
```

11. 已完成窗口 11 专属测试：

```text
7 passed
```

12. 已完成全量测试：

```text
114 passed
```

13. 已验证 `evaluation_result` 有新评测结果入库。

---

### 3.1 本窗口未完成 / 未越权实现

- 未新增数据库表；
- 未新增 Alembic migration；
- 未修改 `evaluation_case` / `evaluation_result` 表结构；
- 未修改 RAG 主流程；
- 未修改 Agent 状态结构；
- 未修改 Prompt 管理协议；
- 未修改模型网关协议；
- 未接入 Ragas 真实外部评测模型；
- 未做窗口 12 的 Prometheus / Grafana / OpenTelemetry。

---

## 四、新增文件清单

```text
backend/app/api/v1/evaluations.py
backend/app/evaluations/agent_eval.py
backend/app/evaluations/metrics.py
backend/app/evaluations/rag_eval.py
backend/app/repositories/evaluation_repository.py
backend/app/schemas/evaluation.py
backend/app/services/evaluation_service.py
backend/tests/test_evaluation_api.py
backend/tests/test_evaluation_metrics.py
docs/window11_handoff.md
```

说明：

```text
backend/app/evaluations/__init__.py 原文件已存在，本窗口补充模块说明。
当前仓库中窗口 8 / 9 / 10 仍存在未提交文件，它们不是窗口 11 的新增文件。
```

---

## 五、修改文件清单

### 5.1 文件 1：`backend/app/api/v1/router.py`

| 项目     | 内容                                                   |
|--------|------------------------------------------------------|
| 修改内容   | 引入 `evaluations_router`，注册 `/api/v1/evaluations` 路由  |
| 修改原因   | 对外暴露评测中心 API                                         |
| 是否影响下游 | 是                                                    |
| 影响说明   | 前端后台、演示脚本、后续窗口 12 可通过 `/api/v1/evaluations` 访问评测中心能力 |
| 是否破坏上游 | 否                                                    |

---

### 5.2 文件 2：`backend/app/evaluations/__init__.py`

| 项目     | 内容                                    |
|--------|---------------------------------------|
| 修改内容   | 补充评测中心模块说明                            |
| 修改原因   | 明确 `app/evaluations` 是执行窗口 11 的评测逻辑目录 |
| 是否影响下游 | 否                                     |

---

## 六、数据库变更

### 6.1 新增数据表

无。

本窗口未新增任何数据库表。

---

### 6.2 修改数据表

无。

本窗口未修改已有表结构。

---

### 6.3 Alembic 迁移

无新增 Alembic migration。

本窗口直接复用执行窗口 2 已创建的表：

```text
evaluation_case
evaluation_result
```

---

### 6.4 使用到的已有表

#### `evaluation_case`

用于保存评测用例。

核心字段：

```text
id
tenant_id
case_no
case_type
name
description
input_json
expected_output_json
reference_context_json
tags_json
status
metadata_json
created_at
updated_at
deleted_at
```

---

#### `evaluation_result`

用于保存评测结果。

核心字段：

```text
id
tenant_id
request_id
case_id
run_no
target_type
target_id
status
score
answer_relevance
faithfulness
context_recall
context_precision
tool_call_success_rate
agent_task_success_rate
latency_ms
token_cost
input_summary
output_summary
error_message
metrics_json
metadata_json
created_at
```

---

### 6.5 入库验证结果

已执行：

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select target_type, status, run_no, score, answer_relevance, tool_call_success_rate, agent_task_success_rate, created_at from evaluation_result order by created_at desc limit 10;"
```

验证结果包含：

```text
rag                    | success | EVAL_RAG_RUN_xxx | 0.3295 | 0.2500
customer_service_agent | success | EVAL_RUN_xxx     | 1.0000 | 1.0000 | 1.0000 | 1.0000
```

说明：

- RAG 评测结果已写入 `evaluation_result`；
- Agent 评测结果已写入 `evaluation_result`；
- 工具调用成功率和 Agent 任务成功率已写入；
- 不是控制台打印型评测。

---

## 七、API 接口清单

### 7.1 创建评测用例

```http
POST /api/v1/evaluations/cases
```

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "case_no": "EVAL_CS_ORDER_001",
  "case_type": "customer_service_agent",
  "name": "客服订单查询评测用例",
  "description": "验证客服 Agent 能识别订单查询并调用订单详情工具",
  "input_json": {
    "session_id": "eval_session_001",
    "user_no": "U100001",
    "message": "我的订单 O100001 到哪了？",
    "context": {
      "order_no": "O100001"
    }
  },
  "expected_output_json": {
    "intent": "order_query",
    "handoff_required": false,
    "expected_tools": [
      "get_order_detail"
    ],
    "answer": "订单 O100001 已送达"
  },
  "reference_context_json": [],
  "tags_json": [
    "customer_service",
    "order"
  ]
}
```

---

### 7.2 查询评测用例列表

```http
GET /api/v1/evaluations/cases
```

查询参数：

```text
tenant_id
page
page_size
case_type
status
keyword
```

---

### 7.3 查询评测用例详情

```http
GET /api/v1/evaluations/cases/{case_id}
```

查询参数：

```text
tenant_id
```

---

### 7.4 更新评测用例

```http
PATCH /api/v1/evaluations/cases/{case_id}
```

---

### 7.5 归档评测用例

```http
DELETE /api/v1/evaluations/cases/{case_id}
```

说明：

```text
使用软归档
不物理删除评测用例
```

---

### 7.6 执行 RAG 评测

```http
POST /api/v1/evaluations/rag/run
```

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "case_ids": [
    "case_uuid"
  ],
  "run_no": "EVAL_RAG_RUN_001",
  "target_id": "hybrid_opensearch_default",
  "top_k": 5,
  "metadata_json": {
    "strategy_id": "hybrid_opensearch_default"
  }
}
```

执行逻辑：

```text
evaluation_case
  -> KnowledgeService.ask()
  -> RAG answer + citations
  -> EvaluationMetricCalculator
  -> evaluation_result
```

---

### 7.7 执行 Agent 评测

```http
POST /api/v1/evaluations/agents/run
```

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "agent_type": "customer_service",
  "case_ids": [
    "case_uuid"
  ],
  "run_no": "EVAL_RUN_001",
  "target_id": "customer_service_agent_v1"
}
```

支持 Agent 类型：

```text
customer_service
shopping_guide
operation_copilot
```

执行逻辑：

```text
evaluation_case
  -> 对应 AgentService.chat()
  -> Agent response
  -> EvaluationMetricCalculator
  -> evaluation_result
```

---

### 7.8 查询评测结果

```http
GET /api/v1/evaluations/results
```

查询参数：

```text
tenant_id
page
page_size
run_no
target_type
target_id
case_id
status
```

---

### 7.9 查询评测报告

```http
GET /api/v1/evaluations/report
```

查询参数：

```text
tenant_id
run_no
target_type
```

返回内容包括：

```text
total
success_count
failed_count
avg_score
avg_answer_relevance
avg_faithfulness
avg_context_recall
avg_context_precision
avg_tool_call_success_rate
avg_agent_task_success_rate
items
```

---

### 7.10 Prompt 版本对比

```http
POST /api/v1/evaluations/compare/prompts
```

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "prompt_version_ids": [
    "prompt_version_uuid_1",
    "prompt_version_uuid_2"
  ],
  "run_no": "PROMPT_COMPARE_RUN_001"
}
```

当前第一版逻辑：

```text
不重新调用模型
基于已入库 evaluation_result 做聚合对比
target_type = prompt
target_id = prompt_version_id
```

---

### 7.11 检索策略对比

```http
POST /api/v1/evaluations/compare/retrieval
```

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "strategies": [
    {
      "strategy_id": "hybrid_default",
      "vector_weight": 0.65,
      "keyword_weight": 0.35,
      "top_k": 5
    },
    {
      "strategy_id": "keyword_heavy",
      "vector_weight": 0.35,
      "keyword_weight": 0.65,
      "top_k": 5
    }
  ],
  "run_no": "RETRIEVAL_COMPARE_RUN_001"
}
```

当前第一版逻辑：

```text
不动态修改 RAG 全局配置
基于已入库 evaluation_result 做聚合对比
target_type = rag
target_id = strategy_id
```

---

## 八、配置项说明

本窗口未新增环境变量。

继续复用已有配置项：

```text
DATABASE_URL
REDIS_URL
DEFAULT_LLM_PROVIDER
DEFAULT_LLM_MODEL
DEFAULT_EMBEDDING_PROVIDER
DEFAULT_EMBEDDING_MODEL
LLM_BASE_URL
LLM_API_KEY
LLM_TIMEOUT_SECONDS
LLM_MAX_RETRIES
RAG_VECTOR_COLLECTION
RAG_VECTOR_SIZE
RAG_TOP_K
RAG_VECTOR_WEIGHT
RAG_KEYWORD_WEIGHT
```

说明：

- 评测中心本身不直接读取模型 API Key；
- RAG 评测通过 `KnowledgeService` 间接使用 RAG / ModelGateway；
- Agent 评测通过各 Agent Service 间接使用 PromptService / ModelGateway；
- 不绕过任何上游公共能力。

---

## 九、运行方式

### 9.1 启动服务

```bash
cd D:\omni-commerce-ai
docker compose up -d --build backend
```

---

### 9.2 健康检查

```bash
curl.exe "http://127.0.0.1:8002/api/v1/health"
```

---

### 9.3 评测中心接口验证

创建评测用例后，可调用：

```http
POST http://127.0.0.1:8002/api/v1/evaluations/agents/run
GET  http://127.0.0.1:8002/api/v1/evaluations/results
GET  http://127.0.0.1:8002/api/v1/evaluations/report
```

---

## 十、测试方式

### 10.1 窗口 11 专属测试

```powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/test_evaluation_metrics.py tests/test_evaluation_api.py -q
```

已验证结果：

```text
7 passed in 1.33s
```

---

### 10.2 全量测试

```powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/ -q
```

已验证结果：

```text
114 passed in 20.20s
```

---

### 10.3 数据库入库验证

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select target_type, status, run_no, score, answer_relevance, tool_call_success_rate, agent_task_success_rate, created_at from evaluation_result order by created_at desc limit 10;"
```

已验证结果：

```text
rag                    | success | EVAL_RAG_RUN_xxx | 0.3295 | 0.2500
customer_service_agent | success | EVAL_RUN_xxx     | 1.0000 | 1.0000 | 1.0000 | 1.0000
```

---

## 十一、局部实现决策

### 决策 1：第一版使用确定性自定义评测指标，不直接依赖外部评测模型

| 项目      | 内容                                                                                                                        |
|---------|---------------------------------------------------------------------------------------------------------------------------|
| 决策内容    | 使用 `EvaluationMetricCalculator` 实现轻量、确定性、可复现的指标计算                                                                         |
| 指标范围    | `answer_relevance`、`faithfulness`、`context_recall`、`context_precision`、`tool_call_success_rate`、`agent_task_success_rate` |
| 决策原因    | 自动化测试不能依赖真实 LLM API Key；当前项目已有 mock provider，第一版评测需要稳定可回归；外部评测模型接入会带来成本、速度和不确定性                                           |
| 影响范围    | 当前评分是启发式规则评分，不代表最终语义评测上限                                                                                                  |
| 后续可调整方式 | 后续可接入 Ragas 或 LLM-as-judge，但保持 `evaluation_result` 入库字段不变                                                                 |

---

### 决策 2：RAG 评测调用 `KnowledgeService.ask()`，不直接调用 RAG 内部组件

| 项目      | 内容                                                                               |
|---------|----------------------------------------------------------------------------------|
| 决策内容    | RAG 评测通过 `KnowledgeService.ask()` 执行完整 RAG 问答链路                                  |
| 决策原因    | 避免绕过窗口 6 已完成的 `PromptService`、`ModelGateway`、`HybridRetriever`、`CitationBuilder` |
| 影响范围    | RAG 评测会实际触发 RAG 检索、Prompt 渲染和模型网关调用                                              |
| 后续可调整方式 | 如果需要评估单独检索阶段，可新增 retrieval-only 评测执行器，但必须继续写入 `evaluation_result`                |

---

### 决策 3：Agent 评测调用各 Agent Service，不直接调用 LangGraph 节点

| 项目      | 内容                                                                                                                                                        |
|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| 决策内容    | `customer_service` 调用 `CustomerServiceAgentService`；`shopping_guide` 调用 `ShoppingGuideAgentService`；`operation_copilot` 调用 `OperationCopilotAgentService` |
| 决策原因    | 避免绕过 Agent service 层对工具、Prompt、模型网关和日志服务的统一编排。评测更接近真实 API 行为                                                                                              |
| 影响范围    | Agent 评测会产生真实 `agent_task`、`tool_call_log`、`model_call_log`                                                                                               |
| 后续可调整方式 | 可增加“节点级评测”，但不能替代完整 Agent 任务评测                                                                                                                             |

---

### 决策 4：Prompt 版本对比第一版基于已入库结果聚合

| 项目      | 内容                                                                                                                  |
|---------|---------------------------------------------------------------------------------------------------------------------|
| 决策内容    | `/compare/prompts` 不直接重新调用模型，而是基于 `evaluation_result` 中 `target_type=prompt`、`target_id=prompt_version_id` 的结果做聚合对比 |
| 决策原因    | 当前窗口 11 不能修改 Prompt 管理协议，也不能擅自设计 Prompt 灰度执行器。先建立对比报告合同，后续可扩展真实批量重跑                                                 |
| 影响范围    | 调用方需要先通过评测执行产生对应 Prompt 版本结果                                                                                        |
| 后续可调整方式 | 后续可新增“按 Prompt Version 重新渲染并执行目标任务”的批量评测能力                                                                          |

---

### 决策 5：检索策略对比第一版基于 `strategy_id` 聚合

| 项目      | 内容                                                                    |
|---------|-----------------------------------------------------------------------|
| 决策内容    | `/compare/retrieval` 使用 `strategy_id` 作为 `target_id`，对已入库 RAG 评测结果做聚合 |
| 决策原因    | 当前 RAG 检索权重是配置项，窗口 11 不擅自动态修改全局 RAG 配置。先让评测报告具备策略对比结构                 |
| 影响范围    | 需要调用方在执行不同策略时，用不同 `target_id` 记录结果                                    |
| 后续可调整方式 | 后续可增加临时参数化 `HybridRetriever` 的能力，但需要总控确认是否允许修改 RAG 调用合同               |

---

### 决策 6：评测失败也写入 `evaluation_result`

| 项目      | 内容                                                                           |
|---------|------------------------------------------------------------------------------|
| 决策内容    | 单条 RAG / Agent 执行失败时，仍创建 `evaluation_result`，状态为 `failed`，记录 `error_message` |
| 决策原因    | 真实评测任务中，失败结果也是评测结果。不能因为某条 case 失败就让整批结果消失                                    |
| 影响范围    | 评测报告可以统计 `success_count` / `failed_count`                                    |
| 后续可调整方式 | 后续可增加批次表或异步任务表，支持更完整的失败重试                                                    |

---

## 十二、已知问题

1. 当前评测指标是启发式确定性评分，不是 Ragas 或 LLM-as-judge 的最终语义评测；
2. 当前 Prompt 版本对比和检索策略对比基于已入库结果聚合，不会自动重跑所有 case；
3. 当前未新增 `evaluation_run` 批次表，使用 `run_no` 字段表示评测批次；
4. 当前评测执行是同步 API，未接异步任务队列；大量 case 评测时可能需要后续窗口增强；
5. 当前全量测试仍存在一个既有 `asyncpg` warning：

```text
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
```

该 warning 在窗口 11 前已存在，不阻塞本窗口交付。

6. 当前 RAG 评测会依赖知识库数据是否已初始化；测试中允许 RAG 单条结果为 `success` 或 `failed`
   ，但必须写入 `evaluation_result`；
7. 当前认证 / RBAC 尚未完成，`tenant_id` 仍由请求参数或请求体显式传入。

---

## 十三、需总控确认事项

暂无阻塞事项。

---

### 13.1 后续建议事项 1：是否新增 `evaluation_run` 批次表

| 项目       | 内容                                                                       |
|----------|--------------------------------------------------------------------------|
| 原因       | 当前使用 `run_no` 表示批次，足够支撑第一版。如果后续需要记录评测任务状态、开始时间、结束时间、执行人、环境、模型版本等，建议新增批次表 |
| 影响范围     | 评测中心、前端评测任务列表、窗口 12 可观测性                                                 |
| 当前临时处理   | 使用 `evaluation_result.run_no` 聚合                                         |
| 建议方案     | 后续新增 `evaluation_run` 表，但需要总控确认                                          |
| 是否阻塞下一窗口 | 不阻塞                                                                      |

---

### 13.2 后续建议事项 2：是否接入 Ragas / LLM-as-judge

| 项目       | 内容                                                             |
|----------|----------------------------------------------------------------|
| 原因       | 当前启发式评分稳定但语义能力有限                                               |
| 影响范围     | RAG 评测、Agent 回答质量评测、模型调用成本                                     |
| 当前临时处理   | 使用确定性自定义指标                                                     |
| 建议方案     | 后续在不改变 `evaluation_result` 入库合同的前提下，增加 Ragas 或 LLM-as-judge 指标 |
| 是否阻塞下一窗口 | 不阻塞                                                            |

---

### 13.3 后续建议事项 3：是否支持异步评测任务

| 项目       | 内容                                    |
|----------|---------------------------------------|
| 原因       | 当前同步 API 适合小批量评测；大批量评测会占用请求时间         |
| 影响范围     | 评测中心、任务队列、可观测性、前端进度展示                 |
| 当前临时处理   | 同步执行                                  |
| 建议方案     | 后续接入 Celery / Dramatiq，并在窗口 12 追踪评测任务 |
| 是否阻塞下一窗口 | 不阻塞                                   |

---

## 十四、给下一个执行窗口的注意事项

执行窗口 12 是可观测性与部署交付，接手时请注意：

1. 可以将评测中心接口纳入 Prometheus API 延迟和错误率监控；
2. 可以为评测执行链路增加 OpenTelemetry trace；
3. 可以将 `evaluation_result` 的成功率、平均分、失败数做成 Grafana 面板；
4. 评测中心当前同步执行，大批量评测建议后续改为异步任务；
5. 不要修改窗口 11 已定义的 `/api/v1/evaluations` API 合同，除非总控确认；
6. 如果要新增 `evaluation_run` 批次表，必须先总控确认；
7. 如果接入 Ragas 或 LLM-as-judge，仍必须把结果写入 `evaluation_result`，不能只在日志或控制台展示；
8. 不要绕过 RAG / Agent / Prompt / ModelGateway 现有链路做评测；
9. 当前 `run_no` 是评测批次聚合字段，窗口 12 可基于它做报告和面板展示；
10. 当前 `asyncpg` warning 是既有问题，建议在窗口 12 统一排查测试环境连接生命周期，不要在窗口 11 回头乱改。

---

## 十五、简历可沉淀亮点

> 原文在该小节标题处截止。后续如果你补充具体亮点内容，可以继续接在这里。

可以先临时放入以下版本：

```text
负责评测中心模块建设，基于 FastAPI、SQLAlchemy、PostgreSQL 实现 RAG、Agent、Prompt 和检索策略的评测闭环；设计 evaluation_case / evaluation_result 评测数据流，支持评测用例管理、RAG 评测执行、Agent 评测执行、答案相关性、忠实度、上下文召回、工具调用成功率、Agent 成功率等指标计算，并提供评测报告、Prompt 版本对比和检索策略对比接口。窗口 11 专属测试 7 passed，全量测试 114 passed。
```

---

## 十六、交接结论

执行窗口 11 已完成评测中心的核心工程闭环。

当前已经具备：

1. 评测用例管理；
2. RAG 评测执行；
3. Agent 评测执行；
4. 答案相关性评估；
5. 忠实度评估；
6. 上下文召回评估；
7. 上下文精确率评估；
8. 工具调用成功率统计；
9. Agent 成功率统计；
10. 评测结果入库；
11. 评测报告接口；
12. Prompt 版本对比接口；
13. 检索策略对比接口；
14. 自动化测试。

最终验收结果：

```text
窗口 11 专属测试：7 passed in 1.33s
全量测试：114 passed in 20.20s
```

结论：

```text
窗口 11 当前可以交付。
未新增数据库表。
未新增 Alembic migration。
未绕过 evaluation_result。
未绕过 RAG / Agent / Prompt / ModelGateway。
未越权实现窗口 12 可观测性部署。
```