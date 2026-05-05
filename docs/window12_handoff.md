# 模块交接文档：执行窗口 12 - 可观测性与部署交付

## 一、模块目标

执行窗口 12 负责项目最终收口，不再继续堆业务功能，而是把执行窗口 1～11 的成果整理成一个：

- 能启动；
- 能演示；
- 能测试；
- 能排查；
- 能讲清楚；
- 能写进简历。

的企业级大模型应用项目。

本窗口重点是：

- 部署交付；
- README；
- 演示脚本；
- 真实模型 smoke test；
- 可观测性说明；
- 样例知识库；
- 最终交接；
- 简历亮点沉淀。

本窗口不是功能开发窗口，不重构前面窗口的核心业务链路。

---

## 二、窗口识别结果

| 项目             | 内容                              |
|----------------|---------------------------------|
| 当前执行窗口         | 执行窗口 12                         |
| 当前窗口名称         | 可观测性与部署交付                       |
| 本窗口目标          | 完成项目最终交付收口                      |
| 项目名称           | 智营 OmniCommerce AI：电商企业级大模型运营中台 |
| 当前定位           | 电商企业级大模型应用中台                    |
| 是否新增业务模块       | 否                               |
| 是否修改核心业务主链     | 否                               |
| 是否改 RAG 主流程    | 否                               |
| 是否改 Agent 主流程  | 否                               |
| 是否改评测中心 API 合同 | 否                               |
| 是否允许进入最终验收     | 是                               |

---

## 三、本窗口完成范围

本窗口完成以下内容：

1. 更新最终版 README；
2. 新增部署与启动说明；
3. 新增可观测性与日志查询说明；
4. 新增最终演示脚本；
5. 新增简历亮点沉淀文档；
6. 新增真实模型 smoke test 脚本；
7. 新增导购 RAG 选购知识库样例；
8. 明确端口和测试地址；
9. 明确默认测试使用 mock；
10. 明确真实模型 smoke test 不纳入默认 pytest；
11. 明确 API Key 安全边界；
12. 明确 asyncpg warning 为非阻塞已知问题；
13.

整理 `model_call_log` / `rag_retrieval_log` / `agent_task` / `tool_call_log` / `evaluation_result` / `content_asset` / `content_review`
查询示例；

14. 整理最终演示链路和面试讲解点。

---

## 四、本窗口禁止事项执行情况

本窗口遵守以下禁止事项：

1. 未重构 RAG 主流程；
2. 未重构客服 Agent 主流程；
3. 未重构导购 Agent 主流程；
4. 未重构运营 Copilot 主流程；
5. 未重构内容生成审核流；
6. 未修改评测中心 API 合同；
7. 未新增大型业务模块；
8. 未新增活动表；
9. 未新增行为埋点表；
10. 未新增指标表；
11. 未把真实 API Key 写入代码；
12. 未把真实 API Key 写入 README；
13. 未让 pytest 默认依赖真实大模型；
14. 未绕过 ModelGateway 调真实模型；
15. 未绕过 PromptService 写死 Prompt；
16. 未为了压 warning 大改业务代码。

---

## 五、当前现场状态

窗口 12 接手前已确认：

```text
Docker 服务正常
Alembic head = d62c219e9482
健康检查正常
全量测试 = 117 passed, 1 warning
```

健康检查地址：

```bash
curl.exe "http://127.0.0.1:8002/api/v1/health"
```

当前实际后端访问地址：

```text
http://127.0.0.1:8002
```

端口映射：

```text
宿主机 8002 -> 容器内 8000
```

重要说明：

```text
如果测试打到 127.0.0.1:8000，可能出现大量 404。
这不是业务失败，是端口错误。
```

---

## 六、新增文件清单

### 6.1 文档文件

```text
docs/deployment_guide.md
docs/observability_guide.md
docs/demo_script.md
docs/resume_highlights.md
docs/window12_handoff.md
```

---

### 6.2 样例知识库文件

```text
docs/sample_knowledge/shopping_guide_office_appliance.md
docs/sample_knowledge/shopping_guide_electric_kettle.md
docs/sample_knowledge/shopping_guide_bluetooth_headphone.md
docs/sample_knowledge/shopping_guide_material_safety.md
```

---

### 6.3 脚本文件

```text
backend/scripts/smoke_test_real_llm.py
```

---

## 七、修改文件清单

### 7.1 `README.md`

修改内容：

- 重写为最终交付版 README；
- 统一项目定位为“智营 OmniCommerce AI：电商企业级大模型运营中台”；
- 明确当前技术栈为 PostgreSQL，不沿用早期 MySQL 口径；
- 明确宿主机后端端口为 `8002`；
- 补充核心模块说明；
- 补充启动方式；
- 补充环境变量说明；
- 补充测试方式；
- 补充真实模型 smoke test；
- 补充可观测性与演示脚本入口；
- 补充已知边界和后续优化。

---

## 八、数据库变更

### 8.1 新增数据表

无。

窗口 12 未新增数据库表。

---

### 8.2 修改数据表

无。

窗口 12 未修改任何已有表结构。

---

### 8.3 Alembic 迁移

无新增 Alembic migration。

当前最新迁移版本由窗口 10 提供：

```text
d62c219e9482_create_content_asset_and_review.py
```

当前数据库 head：

```text
d62c219e9482
```

---

## 九、API 变更

窗口 12 未新增 API。

窗口 12 未修改现有 API 合同。

当前项目核心 API 包括：

```text
/api/v1/health
/api/v1/products
/api/v1/orders
/api/v1/aftersales
/api/v1/tickets
/api/v1/llm
/api/v1/prompts
/api/v1/knowledge
/api/v1/agents/customer-service/chat
/api/v1/agents/shopping-guide/chat
/api/v1/agents/operation-copilot/chat
/api/v1/content
/api/v1/evaluations
```

---

## 十、部署与启动说明

详见：

```text
docs/deployment_guide.md
```

核心启动命令：

```bash
cd D:\omni-commerce-ai
docker compose up -d --build
```

健康检查：

```bash
curl.exe "http://127.0.0.1:8002/api/v1/health"
```

测试命令：

```powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/ -q
```

---

## 十一、真实模型 Smoke Test

新增脚本：

```text
backend/scripts/smoke_test_real_llm.py
```

设计原则：

- 不纳入默认 pytest；
- 不硬编码 API Key；
- 不打印 API Key；
- 只读取环境变量；
- 失败不影响 mock 全量测试；
- 通过现有 API 验证真实模型链路；
- 不绕过 ModelGateway。

执行方式：

```bash
cd D:\omni-commerce-ai\backend
python scripts/smoke_test_real_llm.py
```

前置环境变量示例：

```powershell
$env:DEFAULT_LLM_PROVIDER="openai_compatible"
$env:DEFAULT_LLM_MODEL="qwen-turbo"
$env:LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:LLM_API_KEY="用户本地自己的 API Key"
```

验证链路包括：

- 健康检查；
- 直接模型网关 Chat；
- RAG 问答；
- 客服 Agent 订单查询；
- 客服 Agent 政策问答；
- 客服 Agent 投诉转人工；
- 导购 Agent 预算推荐；
- 运营 Copilot GMV 查询；
- 内容生成；
- 评测结果查询。

---

## 十二、可观测性说明

详见：

```text
docs/observability_guide.md
```

重点追踪字段：

```text
request_id
agent_task_id
prompt_template_id
prompt_version_id
model_call_log_id
run_no
```

重点日志 / 审计表：

```text
model_call_log
rag_retrieval_log
agent_task
agent_step_log
tool_call_log
evaluation_result
content_asset
content_review
```

---

### 12.1 常用模型调用查询

```sql
select provider,
       model_name,
       call_type,
       status,
       latency_ms,
       input_tokens,
       output_tokens,
       total_tokens,
       request_id,
       created_at
from model_call_log
order by created_at desc limit 20;
```

---

### 12.2 常用 RAG 检索查询

```sql
select query,
       retrieval_mode,
       result_count,
       latency_ms,
       request_id,
       created_at
from rag_retrieval_log
order by created_at desc limit 20;
```

---

### 12.3 常用 Agent 查询

```sql
select agent_type,
       task_no,
       intent,
       status,
       handoff_required,
       request_id,
       created_at
from agent_task
order by created_at desc limit 20;
```

---

### 12.4 常用工具调用查询

```sql
select tool_name,
       tool_type,
       status,
       latency_ms,
       input_summary,
       output_summary,
       created_at
from tool_call_log
order by created_at desc limit 20;
```

---

### 12.5 常用评测查询

```sql
select target_type,
       target_id,
       status,
       run_no,
       score,
       created_at
from evaluation_result
order by created_at desc limit 20;
```

---

### 12.6 常用内容资产查询

```sql
select content_type,
       biz_type,
       biz_id,
       version,
       status,
       review_status,
       model_call_log_id,
       created_at
from content_asset
order by created_at desc limit 20;
```

---

## 十三、演示脚本说明

详见：

```text
docs/demo_script.md
```

演示链路覆盖：

- 商品查询；
- RAG 政策问答；
- 客服 Agent 订单查询；
- 客服 Agent 投诉转人工；
- 导购 Agent 预算推荐；
- 导购 Agent 指定商品 SKU 对比；
- 运营 Copilot GMV 查询；
- 运营 Copilot 低库存分析；
- 内容生成；
- 内容审核；
- 评测中心查询；
- 可观测性 SQL 查询。

每条演示包含：

```text
请求命令
预期关键字段
相关日志查询 SQL
面试讲解点
```

---

## 十四、样例知识库说明

新增目录：

```text
docs/sample_knowledge/
```

新增样例：

```text
shopping_guide_office_appliance.md
shopping_guide_electric_kettle.md
shopping_guide_bluetooth_headphone.md
shopping_guide_material_safety.md
```

目的：

- 补充导购 Agent / RAG 选购知识演示材料；
- 避免导购 RAG 演示时只命中售后政策；
- 提升办公室小家电、电热水壶、蓝牙耳机、材质安全等售前咨询场景的真实性。

上传示例：

```powershell
cd D:\omni-commerce-ai

curl.exe -X POST "http://127.0.0.1:8002/api/v1/knowledge/documents/upload" `
  -F "tenant_id=00000000-0000-0000-0000-000000000001" `
  -F "title=办公室小家电选购指南" `
  -F "language=zh-CN" `
  -F "file=@docs/sample_knowledge/shopping_guide_office_appliance.md"
```

上传后触发：

```text
MinIO 保存原始文件
Parser 解析
Chunk 切片
PostgreSQL 入库
Embedding
Qdrant 入库
OpenSearch 索引
```

---

## 十五、简历亮点沉淀

详见：

```text
docs/resume_highlights.md
```

覆盖模块：

- 总体项目亮点；
- 后端工程架构；
- 数据库建模；
- 模型网关；
- Prompt 管理；
- 企业知识库 RAG；
- 客服 Agent；
- 导购 Agent；
- 运营 Copilot / SQL Guard；
- 内容生成与审核流；
- 评测中心；
- 可观测性；
- 项目测试与交付；
- 面试总述话术；
- 简历精简版项目描述。

---

## 十六、测试方式与验收命令

窗口 12 完成后，应重新执行全量测试：

```powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/ -q
```

窗口 12 接手时已有现场验证：

```text
117 passed, 1 warning
```

最终提交前应再次确认：

- 全量测试仍通过；
- warning 未增加；
- 没有新增 `__pycache__`；
- 没有新增 `.pyc`；
- 没有误删 tracked `tmp_*.json`；
- `git status --short` 中只包含真实业务成果、窗口 12 文档和 smoke test 脚本。

---

## 十七、已知问题

### 17.1 asyncpg warning

当前全量测试存在一个既有 warning：

```text
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
```

当前判断：

- 不影响全量测试通过；
- 不影响健康检查；
- 不影响数据库迁移；
- 不影响主业务链路演示；
- 可能来自测试环境中 asyncpg 连接资源释放时机。

窗口 12 不为压 warning 大改业务主链。

后续可小范围排查：

- pytest fixture；
- httpx 测试调用；
- SQLAlchemy AsyncSession 生命周期；
- asyncpg 连接池关闭时机；
- Windows / Conda 环境事件循环策略。

---

### 17.2 认证 / RBAC 未完成

当前 `tenant_id` 仍通过 query / body 显式传入。

后续如接入认证，应从 JWT 或 request context 注入租户信息。

---

### 17.3 真实模型 smoke test 依赖外部环境

真实模型 smoke test 依赖：

- 本地 API Key；
- 模型服务可用性；
- 网络环境；
- 额度；
- backend 是否读取到环境变量。

因此不纳入默认 pytest。

---

### 17.4 RAG 中文检索可继续增强

当前 OpenSearch 使用默认 analyzer，后续可接 IK Analyzer 或其他中文分词方案。

---

### 17.5 mock embedding 维度与真实 embedding 维度不同

当前 mock embedding 使用 3 维向量。

切换真实 embedding 时，需要同步调整：

```text
RAG_VECTOR_SIZE
Qdrant collection
```

---

## 十八、后续优化建议

后续可继续增强：

1. 接入认证 / RBAC；
2. 新增 `evaluation_run` 批次表；
3. 接入 Ragas / LLM-as-judge；
4. 接入真实 reranker；
5. 增加行为埋点表，完善转化率指标；
6. 接入 Prometheus / Grafana / OpenTelemetry；
7. 增强测试隔离和数据库清理机制；
8. 优化 asyncpg / SQLAlchemy 测试资源释放；
9. 增强 OpenSearch 中文分词；
10. 增加前端后台或管理端演示界面；
11. 增强内容资产多版本重生成能力；
12. 为导购 Agent 增加更正式的排序模型或向量召回。

---

## 十九、交接结论

执行窗口 12 已完成项目最终交付收口。

当前项目已经具备：

- 可启动；
- 可演示；
- 可测试；
- 可排查；
- 可讲清楚；
- 可写进简历。

本窗口没有继续堆业务功能，而是把执行窗口 1～11 的成果整理成一个完整的企业级大模型应用项目。

---

## 二十、真实模型 Smoke Test 修正补丁

### 20.1 背景

窗口 12 初版 `smoke_test_real_llm.py` 只判断 HTTP 200 和 `success=true`，导致以下情况被误判为完全通过：

- `/api/v1/llm/chat` 直连 ModelGateway 已成功走 `openai_compatible + qwen-turbo`
- 但 RAG Ask、客服政策问答、内容生成结果仍出现 `[mock]`
- 脚本仍输出 `All smoke checks returned success=true`

因此该结果只能说明接口连通，不能说明所有业务链路都真实走了 Qwen。

### 20.2 修正内容

已修改：

~~~text
backend/scripts/smoke_test_real_llm.py
~~~

新增校验：

1. `/api/v1/llm/chat` 必须返回 `provider=openai_compatible`；
2. `/api/v1/llm/chat` 必须返回 `model_name=qwen-turbo`；
3. `/api/v1/knowledge/ask` 的 `data.answer` 不能以 `[mock]` 开头；
4. 客服政策问答的 `data.answer` 不能以 `[mock]` 开头；
5. 内容生成的 `data.asset.content` 不能以 `[mock]` 开头；
6. 如果检测到 `[mock]`，脚本必须失败，并输出：

~~~text
业务链路仍在使用 mock provider，请检查 backend 容器 DEFAULT_LLM_PROVIDER / DEFAULT_LLM_MODEL 环境变量，以及 Prompt 版本 model_config_json 是否仍配置为 mock。
~~~

### 20.3 根因定位

真实模型 smoke test 初次修正后，结果显示：

- `/api/v1/llm/chat` 已经真实走 `openai_compatible + qwen-turbo`
- RAG Ask、客服政策问答、内容生成仍返回 `[mock]`

进一步排查发现：

- backend 容器环境变量已是 `DEFAULT_LLM_PROVIDER=openai_compatible`
- 但 active Prompt 的 `model_config_json` 仍是 `provider=mock, model=mock-chat-model`

结论：

~~~text
业务链路优先使用 Prompt 版本中的 model_config_json，而不是只看 backend DEFAULT_LLM_PROVIDER。
~~~

这符合 Prompt 管理模块的设计，但真实模型 smoke test 需要同时切换 backend 环境和相关 Prompt 版本配置。

### 20.4 临时切换方式

真实模型 smoke test 前，可临时将相关 active Prompt 切到 qwen：

~~~sql
update prompt_version pv
set model_config_json =
        jsonb_set(
                jsonb_set(
                        coalesce(pv.model_config_json::jsonb, '{}'::jsonb),
                        '{provider}',
                        to_jsonb('openai_compatible'::text),
                        true
                ),
                '{model}',
                to_jsonb('qwen-turbo'::text),
                true
        ) from prompt_template pt
where pv.template_id = pt.id
  and pt.tenant_id = '00000000-0000-0000-0000-000000000001'
  and pt.deleted_at is null
  and pv.deleted_at is null
  and pv.is_active = true
  and pv.status = 'active'
  and pt.scene in (
    'rag_answer_generation'
    , 'customer_service_intent'
    , 'customer_service_answer'
    , 'content_generation'
    );
~~~

确认：

~~~sql
select pt.scene,
       pt.template_key,
       pv.version,
       pv.is_active,
       pv.status,
       pv.model_config_json
from prompt_template pt
         join prompt_version pv on pv.template_id = pt.id
where pt.tenant_id = '00000000-0000-0000-0000-000000000001'
  and pt.deleted_at is null
  and pv.deleted_at is null
  and pv.is_active = true
  and pv.status = 'active'
  and pt.scene in (
                   'rag_answer_generation',
                   'customer_service_intent',
                   'customer_service_answer',
                   'content_generation'
    )
order by pt.scene, pt.template_key;
~~~

### 20.5 最终 smoke test 结果

临时切换 active Prompt 到 `openai_compatible + qwen-turbo` 后，修正版 smoke test 已通过：

~~~text
Real LLM smoke test PASSED.
Direct ModelGateway and required business chains did not return [mock].
~~~

通过链路包括：

1. `/api/v1/llm/chat`
2. `/api/v1/knowledge/ask`
3. `/api/v1/agents/customer-service/chat` 的 policy_query
4. `/api/v1/content/generate/product-title`

`model_call_log` 已验证出现多条：

~~~text
openai_compatible | qwen-turbo | chat | success
~~~

说明不只是直连模型网关，RAG、客服政策问答、内容生成等业务链路也真实走了 Qwen。

### 20.6 恢复默认配置

真实模型 smoke test 完成后，已恢复 active Prompt 为 mock：

~~~text
content_generation      -> mock / mock-chat-model
customer_service_answer -> mock / mock-chat-model
customer_service_intent -> mock / mock-chat-model
rag_answer_generation   -> mock / mock-chat-model
~~~

恢复 SQL：

~~~sql
update prompt_version pv
set model_config_json =
        jsonb_set(
                jsonb_set(
                        coalesce(pv.model_config_json::jsonb, '{}'::jsonb),
                        '{provider}',
                        to_jsonb('mock'::text),
                        true
                ),
                '{model}',
                to_jsonb('mock-chat-model'::text),
                true
        ) from prompt_template pt
where pv.template_id = pt.id
  and pt.tenant_id = '00000000-0000-0000-0000-000000000001'
  and pt.deleted_at is null
  and pv.deleted_at is null
  and pv.is_active = true
  and pv.status = 'active'
  and pt.scene in (
    'rag_answer_generation'
    , 'customer_service_intent'
    , 'customer_service_answer'
    , 'content_generation'
    );
~~~

恢复后重新执行默认 mock 全量测试：

~~~text
117 passed, 1 warning
~~~

### 20.7 最终结论

真实模型 smoke test 修正补丁完成。

结论：

~~~text
直连 ModelGateway 真实模型链路：通过
RAG Ask 真实模型链路：通过
客服政策问答真实模型链路：通过
内容生成真实模型链路：通过
model_call_log 多条 qwen-turbo chat success：已验证
Prompt 配置已恢复 mock：已完成
默认 mock 全量测试：117 passed, 1 warning
~~~

窗口 12 没有重构 ModelGateway，没有修改 Provider 协议，没有让 pytest 默认依赖真实模型，没有提交真实 API Key，也没有把业务模块硬编码为
qwen-turbo。

真实模型 smoke test 的正确结论是：

> 在 backend 容器环境变量和 active Prompt `model_config_json` 同时切换到 `openai_compatible + qwen-turbo` 后，核心业务链路可以真实走
> Qwen；默认开发和测试环境仍恢复为 mock，以保证自动化测试稳定。

最终判断：

```text
窗口 12 当前可以交付。
项目可以进入最终验收。
```