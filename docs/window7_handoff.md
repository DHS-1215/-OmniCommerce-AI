# 执行窗口 7 交接文档：智能客服 Agent 与 LangGraph 编排

## 一、窗口目标

执行窗口 7 的目标是在现有电商业务系统基础上，新增一个面向客服场景的智能 Agent 能力。

本窗口不是简单做一个“大模型聊天接口”，而是把大模型、业务工具、RAG、转人工策略、执行日志和 LangGraph
工作流编排结合起来，形成一个可观测、可测试、可扩展的企业级智能客服 Agent。

核心目标包括：

1. 支持智能客服对话入口；
2. 支持订单查询、商品咨询、售后查询、售后申请、政策问答、投诉转人工等客服场景；
3. 使用 LangGraph 编排 Agent 工作流；
4. 将订单、商品、售后、工单、知识库能力封装为工具；
5. 接入 Agent 任务日志、步骤日志、工具调用日志；
6. 支持 LLM 意图识别 + 规则护栏；
7. 支持高风险诉求自动转人工；
8. 支持 RAG 政策问答 citations 返回；
9. 保证 Agent API 可测试、可回归。

---

## 二、新增与修改的核心文件

### 2.1 Agent Schema

文件：

```text
backend/app/schemas/agent.py
```

主要定义：

```text
CustomerServiceChatRequest
CustomerServiceChatResponse
AgentToolCallView
AgentCitationView
```

用于智能客服 API 的请求和响应结构。

设计重点：

1. API 不直接暴露 LangGraph 内部状态；
2. 返回 `agent_task_id`，便于追踪一次 Agent 执行；
3. 返回 `intent`、`answer`、`handoff_required`、`tool_calls`、`citations`、`metadata`；
4. 让前端可以看到本轮回答是否触发工具、是否转人工、是否有知识库引用。

---

### 2.2 工具统一返回结构

文件：

```text
backend/app/tools/base.py
```

核心对象：

```text
ToolResult
```

统一所有 Agent 工具返回结构：

```text
success
tool_name
data
error_code
error_message
```

同时提供：

```text
to_plain_data()
business_error_result()
unexpected_error_result()
summarize_value()
tool_result_to_log_summary()
```

设计原因：

1. Agent 不直接消费 service 返回的复杂 ORM / Pydantic 对象；
2. 所有工具成功和失败格式统一；
3. 工具调用日志可以统一记录输入摘要和输出摘要；
4. 后续增加新工具时不用重新设计返回结构。

---

### 2.3 业务工具封装

新增或修改：

```text
backend/app/tools/product_tools.py
backend/app/tools/order_tools.py
backend/app/tools/aftersale_tools.py
backend/app/tools/ticket_tools.py
backend/app/tools/knowledge_tools.py
```

工具层职责：

1. 只调用 service 层；
2. 不直接操作 repository；
3. 不直接写 SQL；
4. 不决定 Agent 策略；
5. 只负责把业务能力包装成 Agent 可调用工具。

已封装能力：

#### ProductTools

```text
list_products
get_product_detail
list_product_skus
get_sku_detail
list_product_reviews
```

#### OrderTools

```text
list_orders
get_order_detail
```

#### AftersaleTools

```text
list_aftersales
get_aftersale_detail
create_aftersale_ticket
```

#### TicketTools

```text
list_tickets
get_ticket_detail
create_customer_service_ticket
```

#### KnowledgeTools

```text
search_knowledge
ask_policy
```

本窗口中完成了 service 方法签名对齐。

窗口 3 和窗口 6 的多个 service 采用：

```python
service.method(db, *, ...)
```

因此工具层也做了对应调整：

```python
ProductTools(db, ProductService())
OrderTools(db, OrderService())
AftersaleTools(db, AfterSaleService())
TicketTools(db, CustomerServiceTicketService())
KnowledgeTools(db, KnowledgeService())
```

这样 Agent 工具可以复用已有业务服务，不破坏原有分层。

---

## 三、短回炉补丁修正内容

总控要求窗口 7 不新增大功能，只补测试和少量必要修正。

本轮短回炉补丁严格控制范围，没有重构窗口 6 RAG、模型网关、Prompt 管理，也没有改数据库结构。

---

### 3.1 售后创建修正

#### 问题

售后申请信息齐全时，没有调用 `create_aftersale_ticket`。

#### 原因

`AfterSaleCreateRequest.evidence_json` 的真实类型是：

```python
list[Any] | None
```

但节点中默认传了：

```python
{}
```

导致 Pydantic `ValidationError`。

#### 修正

```python
"evidence_json": context.get("evidence_json") or []
```

修改位置：

```text
backend/app/agents/customer_service/nodes.py
```

#### 修正后结果

售后申请信息齐全时：

```text
intent = aftersale_apply
create_aftersale_ticket
success = true
metadata.aftersale_mode = create
```

---

### 3.2 RAG 工具签名修正

#### 问题

政策问答调用 `rag_policy_ask`，但工具返回：

```text
AGENT_TOOL_CALL_FAILED
```

#### 原因

`KnowledgeService` 真实方法是 `ask/search`，且需要显式传入 `db`。

真实签名：

```python
ask(self, db, *, tenant_id, question, top_k=None, request_id=None, user_id=None)
search(self, db, *, tenant_id, query, top_k=None, request_id=None, user_id=None)
```

#### 修正

修改文件：

```text
backend/app/tools/knowledge_tools.py
```

将 `KnowledgeTools` 改为接收：

```python
KnowledgeTools(db, KnowledgeService())
```

并在内部调用：

```python
self.knowledge_service.ask(
    self.db,
    tenant_id=tenant_id,
    question=question,
    top_k=top_k,
    request_id=request_id,
    user_id=user_id,
)
```

同时在：

```text
backend/app/agents/customer_service/service.py
```

改为：

```python
knowledge_tools = KnowledgeTools(
    db=self.db,
    knowledge_service=KnowledgeService(),
)
```

#### 修正后结果

七天无理由退货政策问答：

```text
intent = policy_query
rag_policy_ask
success = true
citations 返回 5 条
handoff_required = false
```

---

### 3.3 RAG citations 字段兼容

为了不重构窗口 6 RAG，只在 Agent 节点侧做轻量兼容。

修改位置：

```text
backend/app/agents/customer_service/nodes.py
```

在 `policy_rag_node` 中兼容以下字段：

```python
citations = (
        result.data.get("citations")
        or result.data.get("references")
        or result.data.get("sources")
        or result.data.get("chunks")
        or result.data.get("documents")
        or []
)
```

这样不改变窗口 6 的 RAG 内部实现，只保证 Agent 响应可以正确拿到引用来源。

---

## 四、Agent 内部结构

### 4.1 意图枚举

文件：

```text
backend/app/agents/customer_service/intents.py
```

定义：

```text
product_query
order_query
aftersale_apply
aftersale_query
policy_query
complaint
human_handoff
general_chat
unknown
```

并提供：

```python
normalize_intent()
```

用于把模型输出或规则识别结果归一化。

---

### 4.2 Agent 状态

文件：

```text
backend/app/agents/customer_service/state.py
```

核心状态包括：

```text
tenant_id
user_id
user_no
session_id
request_id
message
conversation_summary
context
agent_task_id
intent
confidence
entities
selected_tools
tool_results
rag_answer
citations
answer
handoff_required
handoff_reason
error_code
error_message
metadata
```

设计原因：

1. LangGraph 节点之间需要统一状态对象；
2. 状态里保存意图、实体、工具结果、RAG 引用、转人工信息；
3. API 响应不会直接返回完整 state，而是由 service 层转换成响应 schema。

---

### 4.3 转人工策略

文件：

```text
backend/app/agents/customer_service/policies.py
```

核心判断：

1. 用户明确要求人工；
2. 包含投诉、赔偿、曝光、报警、律师、消协等高风险关键词；
3. 意图识别置信度过低；
4. 工具调用失败；
5. 政策类问题没有引用来源。

核心函数：

```python
should_handoff()
```

设计重点：

> 转人工不是完全交给模型判断，而是由规则策略兜底。

这是企业级 Agent 的关键点。

模型可以参与识别，但不能让模型单独决定所有风险场景。

---

## 五、LangGraph 节点设计

核心文件：

```text
backend/app/agents/customer_service/nodes.py
```

当前主要节点：

```text
create_agent_task_node
identify_intent_node
order_tool_node
product_tool_node
aftersale_tool_node
policy_rag_node
handoff_tool_node
validate_result_node
generate_answer_node
finalize_task_node
```

---

### 5.1 `create_agent_task_node`

负责创建 Agent 执行任务。

写入：

```text
agent_task
```

并把以下内容写回 state：

```text
agent_task_id
agent_task_no
```

---

### 5.2 `identify_intent_node`

负责客服意图识别。

正常路径：

```text
PromptService.render_prompt(scene="customer_service_intent")
  -> ModelGateway.chat()
  -> parse_llm_intent_response()
```

兜底路径：

```text
rule_based_intent()
```

增强保护：

```text
guarded_rule_based_intent()
```

它解决了 mock 模型或真实模型误判导致的错误路由问题。

优先级设计为：

```text
高风险 / 人工关键词
  > 明确业务上下文，比如 product_no、sku_no、after_sale_ticket_no
  > 规则识别
  > LLM 输出
```

避免出现：

- 商品问题被误判成订单查询；
- 投诉问题先查订单再转人工。

---

### 5.3 `order_tool_node`

负责订单查询。

支持：

1. 有 `order_no`：调用 `get_order_detail`；
2. 没有 `order_no` 但有 `user_no`：调用 `list_orders`；
3. 信息不足：后续回答节点追问。

已验证链路：

```text
用户问：我的订单 O100001 到哪了？
intent = order_query
get_order_detail
返回订单状态、支付状态、履约状态、物流承运商、物流单号
```

---

### 5.4 `product_tool_node`

负责商品咨询。

支持：

1. 有 `sku_no`：查询 SKU 详情；
2. 有 `product_no`：查询商品详情 + SKU 列表；
3. 评价类问题：查询评价；
4. 没有明确编号：按关键词查询商品列表。

已验证链路：

```text
用户问：智营智能恒温电热水壶有哪些规格？
context.product_no = P100001
intent = product_query
get_product_detail
list_product_skus
返回商品规格、价格、库存
```

---

### 5.5 `aftersale_tool_node`

负责售后场景。

支持：

1. 有售后单号：查询售后详情；
2. 售后申请且信息齐全：创建售后单；
3. 有 `user_no` 或 `order_no`：查询售后列表；
4. 信息不足：不强行创建，后续追问。

售后创建要求信息齐全：

```text
user_no
order_no
order_item_id
after_sale_type
reason
```

短回炉补丁后已验证：

- 售后单查询：通过；
- 售后申请信息不足：通过，不会直接创建售后单；
- 售后申请信息齐全：通过，允许 `create_aftersale_ticket`。

设计原则：

> 售后创建必须保守。

不能因为用户说一句“我要退款”就乱建售后单。

---

### 5.6 `policy_rag_node`

负责政策和知识库问答。

调用：

```text
KnowledgeTools.ask_policy()
```

保存：

```text
rag_answer
citations
prompt_template_id
prompt_version_id
```

短回炉补丁后已验证：

```text
用户问：七天无理由退货政策是什么？
intent = policy_query
rag_policy_ask
success = true
citations 返回 5 条
handoff_required = false
```

设计原则：

> 政策类问题必须尽量带 citations。

没有引用来源时，`validate_result_node` 可以触发转人工或谨慎处理。

---

### 5.7 `handoff_tool_node`

负责投诉和人工转接。

调用：

```text
TicketTools.create_customer_service_ticket()
```

会创建：

```text
customer_service_ticket
```

并设置：

```text
handoff_required = true
handoff_reason = ...
```

已验证链路：

```text
用户说：我要投诉，你们不给我赔偿我就曝光
intent = complaint
create_customer_service_ticket
handoff_required = true
不触发 list_orders
```

---

### 5.8 `validate_result_node`

负责统一校验工具结果和风险状态。

判断：

1. 是否需要转人工；
2. 工具是否失败；
3. 政策类问题是否没有 citations；
4. 是否存在低置信度问题。

校验结果写入：

```text
metadata.validation
```

---

### 5.9 `generate_answer_node`

负责最终回答生成。

正常路径：

```text
PromptService.render_prompt(scene="customer_service_answer")
  -> ModelGateway.chat()
```

由于当前 mock 模型会复读 Prompt，本窗口增加了回答兜底判断：

```text
如果模型返回以 [mock] 开头
或者疑似复读 Prompt
则使用 _build_fallback_answer()
```

并对订单、商品、售后、转人工场景做了更像客服的兜底回答。

订单回答示例：

```text
已查询到你的订单 O100001：订单状态为已完成，支付状态为已支付，履约状态为已送达。物流承运商为 SF Express，单号 SF****0001。
```

商品回答示例：

```text
智营智能恒温电热水壶 当前可选规格有：白色标准版，价格 199.00，库存 100。
```

转人工回答示例：

```text
这个问题我已经为你转人工处理，客服会继续跟进。原因：用户表达涉及投诉、赔付、曝光等高风险诉求。
```

---

### 5.10 `finalize_task_node`

负责 Agent 任务收尾。

根据 state 状态标记：

```text
success
failed
handoff
```

---

## 六、LangGraph 工作流编排

核心文件：

```text
backend/app/agents/customer_service/workflow.py
```

流程结构：

```text
create_task
  -> identify_intent
  -> route_by_intent
      -> product_tool
      -> order_tool
      -> aftersale_tool
      -> policy_tool
      -> handoff_tool
      -> no_tool
  -> validate_result
      -> handoff_tool 或 generate_answer
  -> generate_answer
  -> finalize_task
  -> END
```

关键路由函数：

```python
route_by_intent()
route_after_validate()
```

设计要点：

1. 投诉、人工转接可以直接进入 `handoff_tool`；
2. 订单、商品、售后、RAG 工具调用后统一进入 `validate_result`；
3. `validate_result` 发现工具失败、低置信度、政策无引用时，也可以转人工；
4. 避免工具失败后仍然生成看似正常的回答。

---

## 七、Agent Service 封装

核心文件：

```text
backend/app/agents/customer_service/service.py
```

主要类：

```text
CustomerServiceAgentService
```

职责：

1. 组装 `PromptService`；
2. 组装 `ModelGateway`；
3. 组装 `AgentTaskService` / `StepLogService` / `ToolCallLogService`；
4. 组装 `ProductTools` / `OrderTools` / `AfterSaleTools` / `TicketTools` / `KnowledgeTools`；
5. 构建并执行 LangGraph workflow；
6. 将最终 state 转换为 `CustomerServiceChatResponse`。

API 层不直接接触 LangGraph，也不直接组装工具。

---

## 八、API 接口

新增文件：

```text
backend/app/api/v1/agents.py
```

接口：

```http
POST /api/v1/agents/customer-service/chat
```

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "cs_demo_session_001",
  "user_no": "U100001",
  "message": "我的订单 O100001 到哪了？",
  "conversation_summary": "",
  "context": {
    "order_no": "O100001"
  }
}
```

响应核心字段：

```text
session_id
agent_task_id
intent
answer
handoff_required
handoff_reason
tool_calls
citations
metadata
```

路由注册：

```text
backend/app/api/v1/router.py
```

注册到：

```text
/api/v1/agents
```

最终路径：

```text
/api/v1/agents/customer-service/chat
```

---

## 九、依赖变更

本窗口接入 LangGraph。

`backend/pyproject.toml` 新增：

```text
"langgraph>=1.1.6,<1.2.0",
```

说明：

一开始尝试过：

```text
"langgraph>=0.2.60,<0.3.0"
```

但它会导致本地已有的 `langchain 1.2.x` 依赖族冲突。

最终改为：

```text
langgraph>=1.1.6,<1.2.0
```

并已通过 Docker build 验证。

---

## 十、测试新增与修改

### 10.1 原窗口 7 测试文件

新增：

```text
backend/tests/test_customer_service_agent_api.py
```

覆盖三条核心链路：

1. 订单查询；
2. 商品咨询；
3. 投诉转人工。

关键断言包括：

#### 订单查询

```text
intent == order_query
get_order_detail success
handoff_required == false
answer 包含订单号和已送达状态
```

#### 商品咨询

```text
intent == product_query
get_product_detail success
list_product_skus success
handoff_required == false
answer 包含商品信息、规格、价格或库存
```

#### 投诉转人工

```text
intent == complaint
handoff_required == true
create_customer_service_ticket success
不允许出现 list_orders
```

---

### 10.2 短回炉补丁新增测试文件

新增：

```text
backend/tests/test_customer_service_agent_aftersale_rag_api.py
```

覆盖售后链路和 RAG 政策问答。

#### 售后场景覆盖

1. 售后单查询：
    - 提供 `after_sale_ticket_no`；
    - 验证 `get_aftersale_detail` 被调用；
    - 验证工具调用成功。

2. 售后申请信息不足：
    - 用户只说“我要退款”；
    - 不允许直接 `create_aftersale_ticket`；
    - 返回应提示补充必要信息；
    - `metadata.aftersale_mode == need_more_info`。

3. 售后申请信息齐全：
    - `user_no`、`order_no`、`order_item_id`、`after_sale_type`、`reason` 齐全；
    - 允许 `create_aftersale_ticket`；
    - 验证工具调用成功；
    - `metadata.aftersale_mode == create`。

#### RAG 政策问答场景覆盖

1. 用户询问七天无理由退货政策：
    - 必须调用 `rag_policy_ask`；
    - `rag_policy_ask success = true`；
    - 返回 citations；
    - `handoff_required = false`。

2. 政策问答无 citations：
    - 如果 citations 为空；
    - 必须触发转人工或谨慎处理；
    - 不能编造政策答案。

测试风格沿用现有 API 测试：

- 通过 `TEST_API_BASE_URL` / `API_BASE_URL` 指定服务地址；
- 使用 `httpx`；
- 设置 `trust_env=False`，避免系统代理影响 localhost 请求。

---

## 十一、测试命令与结果

### 11.1 Agent 原核心链路测试

```powershell
$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
python -m pytest tests/test_customer_service_agent_api.py -q
```

结果：

```text
3 passed in 1.66s
```

---

### 11.2 短回炉补丁新增测试

```powershell
$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
python -m pytest tests/test_customer_service_agent_aftersale_rag_api.py -q
```

结果：

```text
5 passed in 1.53s
```

---

### 11.3 原窗口 7 相关回归测试

```bash
python -m pytest tests/test_customer_service_agent_api.py tests/test_orders_api.py tests/test_products_api.py tests/test_tickets_api.py -q
```

结果：

```text
23 passed in 3.13s
```

---

### 11.4 合并后总回归测试

```powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"

python -m pytest `
  tests/test_customer_service_agent_api.py `
  tests/test_customer_service_agent_aftersale_rag_api.py `
  tests/test_orders_api.py `
  tests/test_products_api.py `
  tests/test_tickets_api.py `
  -q
```

最终结果：

```text
28 passed in 4.31s
```

说明：

1. Agent API 核心链路通过；
2. 售后查询 / 售后申请链路通过；
3. RAG 政策问答链路通过；
4. 没有破坏订单 API；
5. 没有破坏商品 API；
6. 没有破坏工单 API。

---

## 十二、已验证接口链路

### 12.1 订单查询链路

请求：

```text
我的订单 O100001 到哪了？
```

结果：

```text
intent = order_query
tool_calls = get_order_detail
handoff_required = false
answer 返回订单状态、支付状态、履约状态、物流信息
```

---

### 12.2 商品咨询链路

请求：

```text
智营智能恒温电热水壶有哪些规格？
```

上下文：

```text
context.product_no = P100001
```

结果：

```text
intent = product_query
tool_calls = get_product_detail + list_product_skus
handoff_required = false
answer 返回规格、价格、库存
```

---

### 12.3 投诉转人工链路

请求：

```text
我要投诉，你们不给我赔偿我就曝光
```

结果：

```text
intent = complaint
tool_calls = create_customer_service_ticket
handoff_required = true
handoff_reason = 用户表达涉及投诉、赔付、曝光等高风险诉求
不再误触发 list_orders
```

---

### 12.4 售后单查询链路

请求：

```text
帮我查一下售后单 xxx 的进度
```

上下文：

```text
context.after_sale_ticket_no = xxx
```

结果：

```text
intent = aftersale_query
tool_calls = get_aftersale_detail
handoff_required = false
```

---

### 12.5 售后申请信息不足链路

请求：

```text
我要退款
```

结果：

```text
intent = aftersale_apply
不调用 create_aftersale_ticket
metadata.aftersale_mode = need_more_info
answer 提醒用户补充必要信息
```

---

### 12.6 售后申请信息齐全链路

请求包含：

```text
user_no
order_no
order_item_id
after_sale_type
reason
```

结果：

```text
intent = aftersale_apply
tool_calls = create_aftersale_ticket
create_aftersale_ticket success = true
metadata.aftersale_mode = create
```

---

### 12.7 RAG 政策问答链路

请求：

```text
七天无理由退货政策是什么？
```

结果：

```text
intent = policy_query
tool_calls = rag_policy_ask
rag_policy_ask success = true
citations 返回 5 条
handoff_required = false
```

---

## 十三、关键设计总结

### 13.1 不是纯 LLM Agent

本窗口没有把所有决策都交给模型。

实际采用：

```text
LLM 意图识别 + 规则护栏 + 工具调用 + 校验策略 + 转人工兜底
```

这比简单聊天机器人更可靠。

---

### 13.2 高风险场景规则优先

投诉、赔付、曝光、报警、律师、消协等关键词优先于 LLM 输出。

这样可以避免模型误判导致风险问题被错误处理。

---

### 13.3 明确业务上下文优先

如果 context 里已经有：

```text
product_no
sku_no
after_sale_ticket_no
order_no
```

则优先按明确业务上下文路由。

这解决了 mock 或真实模型误判问题。

---

### 13.4 工具层只调用 service

工具层不直接查库。

链路为：

```text
Agent Node -> Tool -> Service -> Repository / DB
```

这样复用了窗口 3、窗口 6 已有业务校验。

---

### 13.5 全链路可观测

每次 Agent 调用会记录：

```text
agent_task
agent_step_log
tool_call_log
model_call_log
```

后续排查问题时可以知道：

- 模型怎么判断的；
- 调用了哪个工具；
- 工具成功还是失败；
- 为什么转人工；
- 最后回答从 LLM 来还是 fallback 来。

---

### 13.6 政策问答必须依赖引用来源

RAG 政策问答不能只靠模型生成。

要求：

```text
有 citations：可以正常回答
无 citations：必须转人工或谨慎处理
```

这能避免政策、售后规则、退款时效等场景出现“模型编造”。

---

## 十四、当前已知问题与后续增强项

### 14.1 mock 模型回答质量有限

当前 mock provider 会复读 Prompt，因此 `generate_answer_node` 对 mock 输出做了 fallback 兜底。

真实模型接入后，可以逐步减少 fallback 依赖。

---

### 14.2 Agent Step 暂未在 API 响应中展开

当前 response 里保留：

```text
steps = []
```

后续可以从 `agent_step_log` 查询后返回，便于前端展示执行过程。

---

### 14.3 工具结果摘要仍可增强

当前 `tool_calls` 只返回工具名、成功状态、错误码、错误信息。

后续可以按权限返回部分工具摘要，例如：

- 订单状态；
- 物流状态；
- 商品规格数量；
- 售后单号；
- 工单号。

---

### 14.4 售后申请目前只做基础创建

当前售后申请遵守保守原则：

```text
信息不足不创建
信息齐全才创建
```

后续可增强：

- 自动识别退款金额；
- 自动识别证据图片；
- 自动判断是否需要人工审核。

但这些属于后续增强，不在本次短回炉补丁范围内。

---

### 14.5 RAG 无 citations 场景已测试，但依赖具体知识库命中情况

当前政策问答有 citations，测试也覆盖了无 citations 时的安全处理分支。

后续可进一步补充专门的 mock / fixture 方式，但本次没有重构窗口 6 RAG，符合总控要求。

---

## 十五、交接结论

执行窗口 7 已完成智能客服 Agent 的核心工程闭环，并完成总控要求的短回炉补丁。

当前已经具备：

1. LangGraph 工作流编排；
2. LLM 意图识别；
3. 规则护栏；
4. 订单工具调用；
5. 商品工具调用；
6. 售后查询；
7. 售后申请信息不足保护；
8. 售后申请信息齐全创建；
9. 投诉转人工工单创建；
10. RAG 政策问答；
11. citations 返回；
12. 政策无引用安全处理；
13. Agent 任务日志；
14. Agent 步骤日志；
15. 工具调用日志；
16. 模型调用日志；
17. Agent API；
18. 自动化测试。

最终验收命令：

```powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"

python -m pytest `
  tests/test_customer_service_agent_api.py `
  tests/test_customer_service_agent_aftersale_rag_api.py `
  tests/test_orders_api.py `
  tests/test_products_api.py `
  tests/test_tickets_api.py `
  -q
```

最终结果：

```text
28 passed in 4.31s
```

结论：

```text
窗口 7 当前可以交付。
短回炉补丁已完成。
未越界重构窗口 6 RAG、模型网关、Prompt 管理。
未新增数据库结构变更。
```