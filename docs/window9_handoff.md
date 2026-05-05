# 模块交接文档：执行窗口 9 - 运营 Copilot / BI Agent

## 一、模块目标

执行窗口 9 负责实现面向运营人员的数据分析 Agent，支持指标查询、SQL 安全检查、只读 SQL 执行、GMV / 库存 /
转化率等运营指标分析，以及基于真实查询结果的运营报告生成能力。

本窗口重点不是做一个“模型随便写 SQL”的玩具功能，而是实现一条受控 BI Agent 链路：

```text
指标口径管理
  ↓
SQL 生成 / 指标 SQL 构造
  ↓
SQL Guard 安全检查
  ↓
只读 SQL 执行
  ↓
结果解释 / 报告生成
  ↓
Agent 步骤日志与工具调用日志
```

本窗口已按总控裁决执行：

1. 指标元数据第一版不落库，使用 `MetricService` 内置指标口径；
2. 不新增 `metric_definition` 表；
3. 不新增 Alembic 迁移；
4. `conversion_rate` 第一版只注册，不硬算；
5. SQL Guard 是最高优先级能力，SQL 必须先 guard 再执行；
6. SQL 执行只读，并限制最大返回行数；
7. 继续复用 `PromptService`、`ModelGateway`、`agent_task`、`agent_step_log`、`tool_call_log`；
8. 不绕过现有模型网关和日志体系。

窗口 9 原始职责要求包含：

- 指标元数据管理；
- 指标口径定义；
- Text-to-SQL Prompt；
- SQL 安全检查；
- 只读查询执行；
- GMV / 转化率 / 库存分析；
- 活动复盘报告生成；
- BI Agent 步骤日志。

禁止事项包括：

- 禁止模型裸写 SQL 直接执行；
- 禁止危险 SQL；
- 禁止绕过指标口径管理。

---

## 二、窗口识别结果

| 项目                    | 内容                    |
|-----------------------|-----------------------|
| 当前执行窗口                | 执行窗口 9                |
| 当前窗口名称                | 运营 Copilot / BI Agent |
| 当前状态                  | 已完成                   |
| 上游依赖                  | 执行窗口 1、2、3、4、5        |
| 是否新增数据库表              | 否                     |
| 是否新增 Alembic 迁移       | 否                     |
| 是否修改统一响应格式            | 否                     |
| 是否修改模型网关协议            | 否                     |
| 是否修改 Prompt 管理协议      | 否                     |
| 是否越权实现窗口 10 / 11 / 12 | 否                     |
| 建议进入下一窗口              | 是，执行窗口 10：内容生产与审核流    |

---

## 三、已完成内容

### 3.1 指标元数据与指标口径

新增：

```text
MetricService
```

以服务内置方式管理第一版指标口径，不落库。

已注册指标：

```text
gmv
order_count
avg_order_value
inventory_stock
low_stock_sku_count
refund_amount
after_sale_count
review_count
positive_review_count
negative_review_count
conversion_rate
```

核心口径说明：

| 指标                    | 口径                                                                 |
|-----------------------|--------------------------------------------------------------------|
| `gmv`                 | 基于 `order_info.paid_amount` 汇总，只统计 `payment_status = paid` 且未软删除订单 |
| `order_count`         | 基于 `order_info` 统计已支付订单数                                           |
| `avg_order_value`     | 基于 GMV / 已支付订单数                                                    |
| `inventory_stock`     | 基于 `product_sku.stock_quantity` 汇总在售 SKU 库存                        |
| `low_stock_sku_count` | 统计库存小于等于 5 的在售 SKU 数                                               |
| `conversion_rate`     | 已注册，但第一版返回 `data_source_missing`，不允许硬算                             |

---

### 3.2 SQL Guard 安全检查

新增：

```text
SqlGuardService
```

实现只读 SQL 安全检查。

已支持拦截：

- 写操作 SQL；
- 多语句 SQL；
- 非白名单表；
- 无 `tenant_id` 过滤；
- `SELECT *`；
- 危险关键字。

禁止关键字包括：

```text
INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE
COPY
CALL
EXEC
EXECUTE
MERGE
VACUUM
ANALYZE
```

允许表白名单：

```text
order_info
order_item
product
product_sku
product_review
user_profile
after_sale_ticket
customer_service_ticket
```

---

### 3.3 只读 SQL 执行工具

新增：

```text
BITools
```

统一封装运营 Copilot 可调用的 BI 工具。

能力包括：

```text
list_metrics
get_metric_definition
build_metric_query
guard_sql
execute_readonly_sql
```

其中：

```text
execute_readonly_sql
```

内部会再次执行 SQL Guard，不允许绕过安全检查直接执行 SQL。

执行时额外限制最大返回行数，当前默认：

```text
max_rows = 100
```

---

### 3.4 Operation Copilot Agent

新增目录：

```text
backend/app/agents/operation_copilot/
```

采用 LangGraph 受控工作流。

当前工作流节点：

```text
create_task
parse_intent
build_metric_query
guard_sql
execute_sql
generate_answer
finalize_task
```

该工作流不是自由黑箱 Agent，而是明确控制 SQL 生成、SQL Guard、只读执行、回答生成的顺序。

---

### 3.5 API 接口

在已有文件中新增接口：

```text
backend/app/api/v1/agents.py
```

接口：

```http
POST /api/v1/agents/operation-copilot/chat
```

说明：

- 按总控确认路径实现；
- 未新增 `operations.py`；
- 原因是现有客服 Agent、导购 Agent 均挂在 `api/v1/agents.py` 下，本窗口继续复用统一 Agent API 入口；
- 响应继续使用项目统一响应格式；
- 全局规范要求所有 API 必须返回统一响应结构，禁止裸数组、裸字符串或各模块自定义响应格式。

---

### 3.6 Agent 日志

复用已有日志服务：

```text
AgentTaskService
AgentStepLogService
ToolCallLogService
```

已记录：

- Agent 任务；
- Agent 步骤；
- BI 工具调用；
- SQL Guard 结果摘要；
- SQL 执行摘要。

---

### 3.7 运营报告边界

报告生成必须基于真实 `query_result`，不允许模型自由编数据。

当前普通指标查询默认使用规则解释，不强行调用：

```text
operation_report_generation
```

Prompt。

明确进入 `operation_report` 意图时，才尝试使用：

```text
scene = operation_report_generation
```

并且把真实查询结果、指标信息和 SQL 作为变量传入 Prompt。

---

## 四、新增文件清单

```text
backend/app/agents/operation_copilot/__init__.py
backend/app/agents/operation_copilot/state.py
backend/app/agents/operation_copilot/intents.py
backend/app/agents/operation_copilot/nodes.py
backend/app/agents/operation_copilot/workflow.py
backend/app/agents/operation_copilot/service.py

backend/app/schemas/operation_copilot.py

backend/app/services/metric_service.py
backend/app/services/sql_guard_service.py

backend/app/tools/bi_tools.py

backend/tests/test_metric_service.py
backend/tests/test_sql_guard_service.py
backend/tests/test_bi_tools.py
backend/tests/test_operation_copilot_api.py
```

---

## 五、修改文件清单

```text
backend/app/api/v1/agents.py
```

修改内容：

- 新增 `OperationCopilotAgentService` import；
- 新增 `OperationCopilotChatRequest` import；
- 新增接口：

```http
POST /api/v1/agents/operation-copilot/chat
```

未修改：

```text
backend/app/api/v1/router.py
backend/app/llm/gateway.py
backend/app/services/prompt_service.py
backend/app/services/model_call_log_service.py
backend/app/models/*
backend/alembic/*
```

---

## 六、数据库变更

### 6.1 新增数据表

无。

---

### 6.2 修改数据表

无。

---

### 6.3 Alembic 迁移

无。

---

### 6.4 使用到的现有表

业务查询使用：

```text
order_info
order_item
product
product_sku
product_review
user_profile
after_sale_ticket
customer_service_ticket
```

日志复用：

```text
agent_task
agent_step_log
tool_call_log
model_call_log
```

说明：

- 第一版指标元数据不落库；
- `MetricService` 内置指标口径；
- 后续如总控要求运营指标后台可配置，可新增 `metric_definition` 表，但本窗口未做。

---

## 七、API 接口清单

### 7.1 运营 Copilot 对话

```http
POST /api/v1/agents/operation-copilot/chat
```

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "manual_op_gmv_clean_001",
  "user_no": "U100001",
  "message": "帮我查询一下 GMV",
  "conversation_summary": "",
  "context": {
    "metric_key": "gmv"
  }
}
```

响应核心字段：

```json
{
  "session_id": "manual_op_gmv_clean_001",
  "agent_task_id": "uuid",
  "intent": "metric_query",
  "answer": "已完成运营指标查询...",
  "metrics": [],
  "sql_summary": {
    "sql": "SELECT ...",
    "guard": {
      "passed": true,
      "readonly": true,
      "tables": []
    }
  },
  "query_result": {
    "columns": [],
    "rows": [],
    "row_count": 1,
    "limited": false,
    "max_rows": 100
  },
  "report": null,
  "tool_calls": [],
  "metadata": {},
  "handoff_required": false
}
```

手工验证结果：

```text
GMV 手工验证已通过
gmv = 548.00
SQL Guard passed = true
readonly = true
table = order_info
```

返回中：

```text
sql_summary.sql
```

已使用 SQL Guard 归一化后的 SQL，且 metadata 中没有：

```text
operation_report_generation_error
```

---

## 八、配置项说明

本窗口未新增环境变量。

继续沿用已有配置：

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
```

说明：

- 普通指标查询不依赖真实 LLM；
- 报告生成路径会复用 `PromptService` 和 `ModelGateway`；
- 模型调用仍走现有模型网关，不直接调用外部模型 API。

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

### 9.3 运营 Copilot 手工验证

```powershell
cd D:\omni-commerce-ai

@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "manual_op_gmv_clean_001",
  "user_no": "U100001",
  "message": "帮我查询一下 GMV",
  "conversation_summary": "",
  "context": {
    "metric_key": "gmv"
  }
}
'@ | Set-Content -Encoding utf8 .\tmp_operation_copilot_gmv.json

curl.exe -X POST "http://127.0.0.1:8002/api/v1/agents/operation-copilot/chat" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_operation_copilot_gmv.json"

Remove-Item .\tmp_operation_copilot_gmv.json
```

---

## 十、测试方式

### 10.1 窗口 9 相关测试

```powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/test_metric_service.py tests/test_sql_guard_service.py tests/test_bi_tools.py tests/test_operation_copilot_api.py -q
```

结果：

```text
21 passed
```

---

### 10.2 全量测试

```bash
python -m pytest tests/ -q
```

结果：

```text
94 passed, 1 warning
```

最近一次验证中：

```text
窗口 9 相关测试：21 passed
全量测试：94 passed, 1 warning
```

---

### 10.3 说明

本地测试必须设置：

```powershell
$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"
```

原因：

当前 Docker Compose 暴露的宿主机后端端口是：

```text
8002
```

如果测试默认打到：

```text
127.0.0.1:8000
```

会出现大量 HTTP 404。

这不是业务失败，是端口打错。

此前已出现过：

```text
43 failed, 30 passed
```

原因就是测试请求打到了：

```text
127.0.0.1:8000
```

而不是当前 backend 的：

```text
8002
```

---

## 十一、局部实现决策

### 决策 1：指标元数据第一版不落库

| 项目      | 内容                                              |
|---------|-------------------------------------------------|
| 决策内容    | 使用 `MetricService` 内置指标口径                       |
| 决策原因    | 总控裁决第一版不新增 `metric_definition` 表，不新增 Alembic 迁移 |
| 影响范围    | 指标口径更新需要改代码                                     |
| 后续可调整方式 | 如后续需要运营后台配置指标，可新增 `metric_definition` 表，并回总控确认  |

---

### 决策 2：`conversion_rate` 只注册，不硬算

| 项目      | 内容                                         |
|---------|--------------------------------------------|
| 决策内容    | `conversion_rate` 返回 `data_source_missing` |
| 决策原因    | 当前核心表缺少曝光、访问、点击、加购等行为数据源                   |
| 影响范围    | 运营 Copilot 可以识别转化率，但不会伪造转化率结果              |
| 后续可调整方式 | 后续新增埋点表后再补真实转化率口径                          |

---

### 决策 3：SQL Guard 强制在执行前运行

| 项目      | 内容                                      |
|---------|-----------------------------------------|
| 决策内容    | `execute_readonly_sql` 内部再次调用 SQL Guard |
| 决策原因    | 避免外部调用方绕过 `guard_sql` 直接执行 SQL          |
| 影响范围    | 所有 BI SQL 执行都必须通过安全检查                   |
| 后续可调整方式 | 可扩展 SQL AST 解析器，但当前规则足够覆盖第一版安全红线        |

---

### 决策 4：禁止 `SELECT *`

| 项目      | 内容                                  |
|---------|-------------------------------------|
| 决策内容    | SQL Guard 拦截 `SELECT *` 和 `table.*` |
| 决策原因    | 减少敏感字段误查和大结果集风险                     |
| 影响范围    | 模型或内置 SQL 必须显式选择字段                  |
| 后续可调整方式 | 如需例外，应引入字段级白名单，不建议直接放开              |

---

### 决策 5：普通指标查询不调用报告 Prompt

| 项目      | 内容                                                                         |
|---------|----------------------------------------------------------------------------|
| 决策内容    | 只有 `intent = operation_report` 时才尝试调用 `operation_report_generation` Prompt |
| 决策原因    | 普通指标查询应返回可解释的规则结果，不应无意义触发 LLM                                              |
| 影响范围    | 降低模型调用成本，避免 Prompt 变量不匹配导致噪音                                               |
| 后续可调整方式 | 可根据前端参数显式打开“生成报告”                                                          |

---

### 决策 6：API 继续挂在 `agents.py`

| 项目      | 内容                                                              |
|---------|-----------------------------------------------------------------|
| 决策内容    | 新增 `/api/v1/agents/operation-copilot/chat`，没有新增 `operations.py` |
| 决策原因    | 总控确认 API 路径；且现有客服、导购 Agent 均在 `agents.py` 中，保持 Agent API 入口一致   |
| 影响范围    | 窗口 9 的 API 入口属于 Agent API，而不是单独运营资源 API                         |
| 后续可调整方式 | 如后续要做运营后台 CRUD，可新增 `operations.py` 或 `metrics.py`               |

---

## 十二、已知问题

1. 当前 `conversion_rate` 只注册，不计算。原因是缺少曝光、访问、点击、加购等行为数据源；
2. 指标元数据第一版不落库，后续无法通过后台动态配置指标；
3. SQL Guard 当前基于规则和正则实现，不是完整 SQL AST 解析器；
4. 报告生成路径依赖 Prompt 种子数据变量是否匹配；普通指标查询不触发报告 Prompt；
5. 全量测试存在 1 个 SQLAlchemy / asyncpg 资源 warning，来自既有测试链路，不阻塞窗口 9 交付；
6. 当前认证 / RBAC 尚未接入，`tenant_id` 仍由请求体显式传入。

---

## 十三、需总控确认事项

暂无阻塞事项。

已按总控裁决执行：

- 指标元数据第一版不落库；
- `conversion_rate` 不硬算；
- API 路径使用 `/api/v1/agents/operation-copilot/chat`；
- SQL Guard 为最高优先级能力；
- SQL 执行只读且限制最大返回行数；
- 复用 `PromptService`、`ModelGateway`、`agent_task`、`agent_step_log`、`tool_call_log`。

---

### 13.1 后续建议总控确认事项

#### 事项 1：是否在后续窗口新增行为埋点表

| 项目       | 内容                                         |
|----------|--------------------------------------------|
| 原因       | 转化率需要曝光、访问、点击、加购等行为数据                      |
| 影响范围     | 运营分析、活动复盘、转化漏斗                             |
| 当前临时处理   | `conversion_rate` 返回 `data_source_missing` |
| 是否阻塞下一窗口 | 不阻塞                                        |

---

#### 事项 2：是否后续新增指标元数据表

建议表：

```text
metric_definition
```

| 项目       | 内容                   |
|----------|----------------------|
| 原因       | 支持运营后台动态管理指标口径       |
| 当前临时处理   | `MetricService` 内置指标 |
| 是否阻塞下一窗口 | 不阻塞                  |

---

## 十四、给下一个窗口的注意事项

执行窗口 10 是内容生产与审核流。接手时注意：

1. 不要修改窗口 9 的 SQL Guard 逻辑；
2. 不要让内容生成模块直接调用模型 API，必须走 `ModelGateway`；
3. 不要把内容生成 Prompt 写死在业务代码里，必须走 Prompt 管理；
4. 如果后续内容模块需要运营分析结果，只能通过 service 或 API 获取，不要直接绕过 BI 工具查库；
5. 不要新增行为埋点表或指标表，除非总控明确授权；
6. 如果内容审核涉及模型输出，必须保留调用日志、Prompt 版本和审核状态。

---

## 十五、交接结论

执行窗口 9 已完成运营 Copilot / BI Agent 的核心工程闭环。

当前已具备：

1. 指标口径管理；
2. SQL Guard 安全检查；
3. 只读 SQL 执行；
4. 最大返回行数限制；
5. GMV、订单数、客单价、库存、低库存、售后、评价等指标查询；
6. `conversion_rate` 已注册但不硬算；
7. 运营 Copilot Agent 工作流；
8. Agent 日志；
9. 工具调用日志；
10. 统一 Agent API；
11. 自动化测试。

最终验收结果：

```text
窗口 9 相关测试：21 passed
全量测试：94 passed, 1 warning
```

结论：

```text
窗口 9 当前可以交付。
未新增数据库结构。
未新增 Alembic 迁移。
未绕过 SQL Guard。
未绕过 ModelGateway / PromptService。
未越界实现窗口 10 / 11 / 12。
```