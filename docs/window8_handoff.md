# 模块交接文档：执行窗口 8 - 智能导购 Agent

## 一、模块目标

本模块负责实现面向用户购买决策的智能导购 Agent，为电商用户提供基于预算、使用场景、偏好、SKU、库存和评价的结构化商品推荐能力。

本窗口不是简单关键词搜索，也不是让 LLM 编商品推荐，而是在已有商品服务、Prompt 管理、模型网关和 Agent
日志体系基础上，实现一个可解释、可追踪、可测试的智能导购工作流。

核心目标：

1. 用户需求解析；
2. 预算识别；
3. 场景识别；
4. 偏好识别；
5. 商品候选召回；
6. SKU 对比；
7. 评价摘要；
8. 推荐理由生成；
9. 多商品对比输出；
10. 导购话术生成；
11. 导购 Agent 日志。

---

## 二、窗口识别结果

| 项目     | 内容                             |
|--------|--------------------------------|
| 当前执行窗口 | 执行窗口 8                         |
| 当前窗口名称 | 智能导购 Agent                     |
| 本窗口目标  | 实现面向用户购买决策的智能导购 Agent，体现电商转化能力 |

---

### 2.1 本窗口必须完成

- 用户需求解析；
- 预算识别；
- 场景识别；
- 偏好识别；
- 商品候选召回；
- SKU 对比；
- 评价摘要；
- 推荐理由生成；
- 多商品对比输出；
- 导购话术生成；
- 导购 Agent 日志。

---

### 2.2 本窗口禁止完成

- 只做关键词搜索；
- 无理由推荐商品；
- 绕过商品服务直接查库；
- 让 LLM 编造商品 / SKU / 价格 / 库存；
- 修改上游数据库结构；
- 抢做运营 Copilot / 内容生成 / 评测中心。

---

### 2.3 上游依赖

- 执行窗口 1：基础工程骨架；
- 执行窗口 2：核心数据模型；
- 执行窗口 3：基础业务服务；
- 执行窗口 4：模型网关；
- 执行窗口 5：Prompt 管理；
- 执行窗口 7：智能客服 Agent；
- 执行窗口 6：RAG，可作为增强项，非硬依赖。

---

### 2.4 最终交付物

- 智能导购 Agent API；
- `RecommendationService` 推荐规则服务；
- `RecommendationTools` 工具封装；
- Shopping Guide LangGraph 工作流；
- 导购请求 / 响应 Schema；
- 导购 Agent 自动化测试；
- Agent 任务日志和工具调用日志验证。

---

### 2.5 验收标准

- 能根据预算推荐商品；
- 能根据使用场景推荐商品；
- 能对比多个 SKU；
- 能结合评价信息生成推荐理由；
- 能记录推荐过程；
- 输出结果结构化；
- 不推荐 inactive 商品 / SKU；
- 不推荐数据库不存在的商品 / SKU。

---

## 三、已完成内容

已完成：

1. 新增智能导购 API：

```http
POST /api/v1/agents/shopping-guide/chat
```

2. 新增 `ShoppingGuideChatRequest` / `ShoppingGuideChatResponse` 等 Schema。

3. 新增 `RecommendationService`：

    - 解析预算；
    - 解析场景；
    - 解析偏好；
    - 结合用户画像偏好；
    - 召回真实 active 商品；
    - 过滤 active SKU；
    - 判断预算匹配；
    - 判断库存风险；
    - 汇总 visible 评价；
    - 生成结构化 `match_evidence`；
    - 生成规则型 `recommendation_reason`。

4. 新增 `RecommendationTools`：

```text
parse_user_need
recall_product_candidates
compare_product_skus
```

5. 新增 `shopping_guide` Agent：

```text
state
intents
nodes
workflow
service
```

6. 使用 LangGraph 编排导购 Agent 工作流。

7. 创建 `agent_task` 时使用：

```text
agent_type = shopping_guide
```

8. 工具调用日志写入 `tool_call_log`：

```text
tool_type = recommendation
```

9. 接入 `PromptService`：

```text
scene = shopping_guide_recommendation
```

10. 接入 `ModelGateway`：

> LLM 只用于导购话术润色，不参与商品 / SKU / 价格 / 库存判断。

11. 新增导购 Agent API 自动化测试。

12. 完成窗口 8 相关回归和全量测试。

---

### 3.1 未做内容

1. 未新增数据库表；
2. 未修改已有数据库结构；
3. 未修改窗口 3 商品接口合同；
4. 未修改窗口 4 模型网关协议；
5. 未修改窗口 5 Prompt 协议；
6. 未修改窗口 7 客服 Agent 工作流；
7. 未做 BI Agent；
8. 未做内容生产；
9. 未做评测中心。

---

## 四、新增文件清单

```text
backend/app/schemas/shopping_guide.py

backend/app/services/recommendation_service.py

backend/app/tools/recommendation_tools.py

backend/app/agents/shopping_guide/__init__.py
backend/app/agents/shopping_guide/intents.py
backend/app/agents/shopping_guide/state.py
backend/app/agents/shopping_guide/nodes.py
backend/app/agents/shopping_guide/workflow.py
backend/app/agents/shopping_guide/service.py

backend/tests/test_shopping_guide_agent_api.py
```

---

## 五、修改文件清单

### 5.1 文件 1：`backend/app/api/v1/agents.py`

修改内容：

```http
POST /api/v1/agents/shopping-guide/chat
```

修改原因：

> 窗口 8 需要在现有 Agent API 路由下新增智能导购 Agent 对话入口。

是否影响下游：

```text
是，后续前端和演示脚本可以调用该接口进行导购推荐演示。
```

是否破坏上游：

```text
否。未修改原有 /api/v1/agents/customer-service/chat。
```

---

### 5.2 文件 2：可能涉及 `backend/app/api/v1/router.py`

如果 `agents.py` 已在窗口 7 注册，本窗口无需修改。

当前最终路径：

```http
/api/v1/agents/shopping-guide/chat
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

无新增 Alembic 迁移。

---

### 6.4 使用已有表

本窗口复用执行窗口 2 / 7 已有表：

```text
agent_task
agent_step_log
tool_call_log
model_call_log
product
product_sku
product_review
user_profile
prompt_template
prompt_version
```

---

### 6.5 Agent 日志验证

已验证 `agent_task` 中写入：

```text
agent_type = shopping_guide
status = success
intent = shopping_guide / sku_compare
```

已验证 `tool_call_log` 中写入：

```text
tool_type = recommendation
tool_name = parse_user_need
tool_name = recall_product_candidates
```

---

## 七、API 接口清单

### 7.1 接口 1：智能导购 Agent 对话

```http
POST /api/v1/agents/shopping-guide/chat
```

说明：

> 根据用户预算、使用场景、偏好、商品上下文，生成结构化商品推荐和导购话术。

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "sg_demo_session_001",
  "user_no": "U100001",
  "message": "我预算 300 元以内，想买一个适合办公室用的智能小家电，最好安全、省心、评价好一点",
  "conversation_summary": "",
  "context": {
    "budget_max": 300,
    "scenario": "office",
    "preferences": [
      "安全",
      "省心",
      "评价好"
    ]
  }
}
```

响应核心字段：

```text
session_id
agent_task_id
intent
answer
budget
scenario
preferences
recommendations
comparisons
tool_calls
citations
metadata
```

推荐结果包含：

```text
product_no
title
brand
category
matched_skus
review_summary
match_evidence
recommendation_reason
risk_notes
```

`match_evidence` 至少包含：

```text
budget_match
scenario_match
preference_match
stock_risk
review_risk
```

---

## 八、配置项说明

本窗口未新增环境变量。

继续复用已有配置：

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

- 默认 mock provider 可支撑本地测试；
- 真实模型调用仍通过 `ModelGateway`。

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

### 9.3 手工调用导购接口

```powershell
@'
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "sg_demo_session_001",
  "user_no": "U100001",
  "message": "我预算 300 元以内，想买一个适合办公室用的智能小家电，最好安全、省心、评价好一点",
  "conversation_summary": "",
  "context": {
    "budget_max": 300,
    "scenario": "office",
    "preferences": ["安全", "省心", "评价好"]
  }
}
'@ | Set-Content -Encoding utf8 .\tmp_shopping_guide.json

curl.exe -X POST "http://127.0.0.1:8002/api/v1/agents/shopping-guide/chat" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_shopping_guide.json"
```

预期：

```text
success = true
data.intent = shopping_guide
data.recommendations 非空
data.recommendations[0].product_no = P100001
data.recommendations[0].matched_skus[0].sku_no = SKU100001
data.recommendations[0].match_evidence 存在
```

---

## 十、测试方式

### 10.1 导购 Agent 专属测试

```powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/test_shopping_guide_agent_api.py -q
```

结果：

```text
5 passed in 5.42s
```

---

### 10.2 窗口 8 相关回归测试

```powershell
python -m pytest `
  tests/test_shopping_guide_agent_api.py `
  tests/test_products_api.py `
  tests/test_prompt_api.py `
  tests/test_llm_api.py `
  tests/test_customer_service_agent_api.py `
  -q
```

结果：

```text
23 passed in 10.05s
```

---

### 10.3 全量测试

```bash
python -m pytest tests/ -q
```

结果：

```text
73 passed in 13.58s
```

---

### 10.4 数据库验证：`agent_task`

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select agent_type, status, intent, input_summary, output_summary, created_at from agent_task where agent_type = 'shopping_guide' order by created_at desc limit 5;"
```

已验证：

```text
agent_type = shopping_guide
status = success
intent = shopping_guide / sku_compare
```

---

### 10.5 数据库验证：`tool_call_log`

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select tool_name, tool_type, status, input_summary, output_summary, created_at from tool_call_log where tool_type = 'recommendation' order by created_at desc limit 10;"
```

已验证：

```text
tool_name = parse_user_need
tool_name = recall_product_candidates
tool_type = recommendation
status = success
```

---

## 十一、局部实现决策

### 决策 1：推荐依据由 `RecommendationService` 规则生成，LLM 只做表达增强

| 项目      | 内容                                                                                                                                                                                                                              |
|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 决策内容    | 商品候选、SKU 过滤、预算匹配、场景匹配、偏好匹配、库存风险、评价风险由 `ProductService + RecommendationService` 规则完成。LLM 只用于需求解析增强、推荐理由生成和导购话术润色。最终响应中的 `recommendations` / `comparisons` / `product_no` / `sku_no` / `sale_price` / `stock_quantity` 不由 LLM 决定。 |
| 决策原因    | 避免 LLM 编造商品、SKU、价格、库存和推荐依据。保证导购推荐可解释、可追踪、可测试。                                                                                                                                                                                   |
| 影响范围    | 影响 shopping_guide Agent 推荐链路、API 响应结构和测试断言。                                                                                                                                                                                     |
| 后续可调整方式 | 后续如需引入向量召回、学习排序或个性化推荐，可在 `RecommendationService` 内扩展，但仍不能绕过真实商品数据和 service 层。                                                                                                                                                   |

---

### 决策 2：候选召回采用“宽召回、严过滤”

| 项目      | 内容                                                                               |
|---------|----------------------------------------------------------------------------------|
| 决策内容    | 对“智能小家电”等宽泛关键词，不直接作为强过滤条件。如果 keyword 召回为空，则回退到 active 商品池。后续再由预算、SKU、库存、评价等规则过滤。 |
| 决策原因    | 避免用户表达比较宽泛时误杀真实可推荐商品。                                                            |
| 影响范围    | 影响导购候选召回召回率。                                                                     |
| 后续可调整方式 | 后续可引入类目词典、向量召回或 RAG 选购知识增强召回。                                                    |

---

### 决策 3：用户指定 `product_no` 时优先围绕指定商品做 SKU 对比

| 项目      | 内容                                                                                                         |
|---------|------------------------------------------------------------------------------------------------------------|
| 决策内容    | 当 `context.product_no` 存在时，优先调用 `ProductService.get_product_detail()` 获取指定商品。不再走全量商品池排序。对比结果只围绕该商品 SKU 输出。 |
| 决策原因    | 用户明确说“帮我对比 P100001”，Agent 不应转而推荐别的商品。                                                                      |
| 影响范围    | 影响 SKU 对比场景。                                                                                               |
| 后续可调整方式 | 后续可支持多个 `product_no` 对比。                                                                                   |

---

### 决策 4：用户画像偏好中的内部标签做展示映射

| 项目      | 内容                                                                   |
|---------|----------------------------------------------------------------------|
| 决策内容    | 将 `smart_home` 映射为“智能家居”；将 `kitchen` 映射为“厨房场景”；将 `medium` 映射为“中等预算”。 |
| 决策原因    | 避免导购话术中暴露内部标签，提升用户可读性。                                               |
| 影响范围    | 影响推荐理由中的偏好展示。                                                        |
| 后续可调整方式 | 后续可将标签映射抽到配置或字典表。                                                    |

---

### 决策 5：mock 模型输出复读 Prompt 时使用规则 fallback

| 项目      | 内容                                                                                              |
|---------|-------------------------------------------------------------------------------------------------|
| 决策内容    | 如果模型输出以 `[mock]` 开头，使用 `RecommendationService.build_fallback_answer()` 生成导购话术。不让 mock 输出污染用户回答。 |
| 决策原因    | 当前开发环境默认 mock provider，mock 不代表真实模型表达能力。规则 fallback 更稳定，更适合自动化测试。                               |
| 影响范围    | 影响本地开发和测试环境下的 `answer` 字段。                                                                      |
| 后续可调整方式 | 接入真实模型后可减少 fallback 依赖，但结构化推荐仍必须由规则生成。                                                          |

---

## 十二、已知问题

1. 当前导购推荐还不是复杂排序系统，只实现规则型可解释推荐；
2. 当前只支持单商品 SKU 对比，多商品横向对比后续可增强；
3. 当前用户偏好标签映射是代码内局部字典，后续可配置化；
4. 当前未使用 RAG 做选购知识增强，窗口 6 能力后续可接入“选购指南 / 售前政策 / 材质说明”问答；
5. 当前 mock 模型环境下导购话术主要走规则 fallback，真实模型接入后可增强表达质量；
6. 当前测试依赖窗口 2 Demo 数据，如后续种子数据变化，需要同步调整测试断言中的业务编号。

---

## 十三、需总控确认事项

暂无阻塞事项。

---

### 13.1 事项 1：是否在后续窗口引入更正式的推荐排序能力

| 项目       | 内容                                                     |
|----------|--------------------------------------------------------|
| 原因       | 当前窗口 8 使用规则型排序，已满足窗口验收。后续如需更强推荐能力，可增加向量召回、学习排序、点击转化特征。 |
| 影响范围     | `RecommendationService`、评测中心、运营 Copilot                |
| 当前临时处理   | 使用预算、场景、偏好、库存、评价进行规则排序。                                |
| 建议方案     | 后续可在不破坏 API 合同的前提下扩展 ranking 策略。                       |
| 是否阻塞下一窗口 | 不阻塞                                                    |

---

### 13.2 事项 2：是否将标签展示映射配置化

| 项目       | 内容                                                        |
|----------|-----------------------------------------------------------|
| 原因       | 当前 `smart_home` / `kitchen` / `medium` 等内部标签用代码字典映射成中文展示。 |
| 影响范围     | 导购话术、用户画像展示、后续运营后台配置。                                     |
| 当前临时处理   | `RecommendationService` 内部字典映射。                           |
| 建议方案     | 后续可改为配置文件或字典表。                                            |
| 是否阻塞下一窗口 | 不阻塞                                                       |

---

## 十四、给下一个执行窗口的注意事项

执行窗口 9 是运营 Copilot / BI Agent，接手时注意：

1. 不要复用导购 Agent 的规则去做运营分析；
2. 运营 Copilot 应使用指标口径和 SQL 安全检查，不允许模型裸写 SQL 直接执行；
3. 可以参考窗口 8 的 LangGraph 工作流模式和日志记录方式；
4. 可以复用 `agent_task` / `agent_step_log` / `tool_call_log` 记录 Agent 执行过程；
5. 不要修改窗口 8 的 `/api/v1/agents/shopping-guide/chat` 响应合同；
6. 如果后续需要分析导购转化率，可基于 `agent_task.agent_type = shopping_guide` 做统计；
7. 如果评测中心后续评估导购推荐效果，可以使用 `match_evidence` 和 `tool_call_log` 作为结构化评测输入。

---

## 十五、交接结论

执行窗口 8 已完成智能导购 Agent 的核心能力建设。

当前已经具备：

1. 智能导购 Agent API；
2. 用户需求解析；
3. 预算识别；
4. 场景识别；
5. 偏好识别；
6. 商品候选召回；
7. SKU 对比；
8. 评价摘要；
9. 推荐理由生成；
10. 结构化推荐结果；
11. 导购话术生成；
12. Agent 任务日志；
13. 工具调用日志；
14. 自动化测试。

最终验收结果：

```text
导购 Agent 专属测试：5 passed in 5.42s
窗口 8 相关回归测试：23 passed in 10.05s
全量测试：73 passed in 13.58s
```

结论：

```text
窗口 8 当前可以交付。
未新增数据库结构。
未新增 Alembic 迁移。
未绕过商品服务直接查库。
未让 LLM 编造商品 / SKU / 价格 / 库存。
未破坏客服 Agent、模型网关、Prompt 管理和商品 API。
```