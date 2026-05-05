# 可观测性与日志查询说明

本文档说明智营 OmniCommerce AI 如何排查一次请求、一次模型调用、一次 RAG 检索、一次 Agent 执行、一次工具调用、一次评测和一次内容生成审核。

## 1. request_id 链路追踪

系统通过 request_id 串联 API 请求、模型调用、RAG 检索、Agent 执行、工具调用、内容生成和评测中心。

API 响应体中会返回：

~~~text
request_id = req_xxx
~~~

HTTP 响应头中也会包含：

~~~text
X-Request-ID
~~~

排查问题时，优先从 API 响应中拿到 request_id，再查相关日志表。

## 2. 模型调用日志：model_call_log

用途：

- 查看调用了哪个 provider
- 查看模型名
- 查看调用类型
- 查看 token
- 查看耗时
- 查看错误信息
- 关联 Prompt 模板和 Prompt 版本

查询最近模型调用：

~~~sql
select
  provider,
  model_name,
  model_type,
  call_type,
  status,
  latency_ms,
  input_tokens,
  output_tokens,
  total_tokens,
  request_id,
  created_at
from model_call_log
order by created_at desc
limit 20;
~~~

按 request_id 查询：

~~~sql
select
  provider,
  model_name,
  call_type,
  status,
  error_code,
  error_message,
  input_summary,
  output_summary,
  metadata_json,
  created_at
from model_call_log
where request_id = '替换为请求 request_id'
order by created_at desc;
~~~

查看 Prompt 版本追踪：

~~~sql
select
  provider,
  model_name,
  call_type,
  prompt_template_id,
  prompt_version_id,
  status,
  latency_ms,
  request_id,
  created_at
from model_call_log
order by created_at desc
limit 20;
~~~

## 3. RAG 检索日志：rag_retrieval_log

用途：

- 查看 query
- 查看检索模式
- 查看命中 chunk
- 查看命中文档
- 查看向量分、关键词分、最终分
- 查看耗时
- 查看 search / ask 来源

查询最近 RAG 检索：

~~~sql
select
  query,
  retrieval_mode,
  result_count,
  vector_score,
  keyword_score,
  final_score,
  latency_ms,
  request_id,
  created_at
from rag_retrieval_log
order by created_at desc
limit 20;
~~~

查看命中明细：

~~~sql
select
  query,
  retrieved_chunk_ids,
  retrieved_document_ids,
  scores_json,
  metadata_json,
  created_at
from rag_retrieval_log
order by created_at desc
limit 5;
~~~

按 request_id 查询：

~~~sql
select
  query,
  retrieval_mode,
  result_count,
  retrieved_chunk_ids,
  retrieved_document_ids,
  scores_json,
  metadata_json,
  latency_ms,
  created_at
from rag_retrieval_log
where request_id = '替换为请求 request_id'
order by created_at desc;
~~~

## 4. Agent 任务：agent_task

用途：

- 查看 Agent 类型
- 查看任务编号
- 查看意图
- 查看状态
- 查看是否转人工
- 查看输入输出摘要
- 查看 request_id

查询最近 Agent 任务：

~~~sql
select
  agent_type,
  task_no,
  intent,
  status,
  handoff_required,
  latency_ms,
  request_id,
  input_summary,
  output_summary,
  created_at
from agent_task
order by created_at desc
limit 20;
~~~

按 Agent 类型查询：

~~~sql
select
  agent_type,
  intent,
  status,
  handoff_required,
  input_summary,
  output_summary,
  created_at
from agent_task
where agent_type in ('customer_service', 'shopping_guide', 'operation_copilot')
order by created_at desc
limit 20;
~~~

按 request_id 查询：

~~~sql
select
  id,
  agent_type,
  task_no,
  intent,
  status,
  handoff_required,
  latency_ms,
  input_summary,
  output_summary,
  created_at
from agent_task
where request_id = '替换为请求 request_id'
order by created_at desc;
~~~

## 5. Agent 步骤日志：agent_step_log

用途：

- 查看 LangGraph 工作流执行到了哪一步
- 查看每个节点是否成功
- 查看节点耗时
- 查看输入输出摘要

查询最近步骤：

~~~sql
select
  agent_task_id,
  step_name,
  step_order,
  status,
  latency_ms,
  input_summary,
  output_summary,
  created_at
from agent_step_log
order by created_at desc
limit 30;
~~~

按 Agent 任务查询：

~~~sql
select
  step_name,
  step_order,
  status,
  latency_ms,
  input_summary,
  output_summary,
  created_at
from agent_step_log
where agent_task_id = '替换为 agent_task.id'
order by step_order asc;
~~~

## 6. 工具调用日志：tool_call_log

用途：

- 查看 Agent 调用了哪些工具
- 查看工具类型
- 查看工具成功或失败
- 查看工具输入输出摘要
- 查看耗时

查询最近工具调用：

~~~sql
select
  tool_name,
  tool_type,
  status,
  latency_ms,
  input_summary,
  output_summary,
  created_at
from tool_call_log
order by created_at desc
limit 20;
~~~

按工具类型查询：

~~~sql
select
  tool_name,
  tool_type,
  status,
  input_summary,
  output_summary,
  created_at
from tool_call_log
where tool_type in ('business', 'rag', 'recommendation', 'bi')
order by created_at desc
limit 30;
~~~

按 Agent 任务查询：

~~~sql
select
  tool_name,
  tool_type,
  status,
  latency_ms,
  input_summary,
  output_summary,
  created_at
from tool_call_log
where agent_task_id = '替换为 agent_task.id'
order by created_at asc;
~~~

## 7. 评测结果：evaluation_result

用途：

- 查看 RAG / Agent / Prompt / 检索策略评测结果
- 查看分数
- 查看成功率
- 查看 run_no 批次
- 查看指标 JSON

查询最近评测结果：

~~~sql
select
  target_type,
  target_id,
  status,
  run_no,
  score,
  answer_relevance,
  faithfulness,
  context_recall,
  context_precision,
  tool_call_success_rate,
  agent_task_success_rate,
  latency_ms,
  created_at
from evaluation_result
order by created_at desc
limit 20;
~~~

按 run_no 聚合：

~~~sql
select
  run_no,
  target_type,
  count(*) as total,
  sum(case when status = 'success' then 1 else 0 end) as success_count,
  avg(score) as avg_score,
  avg(answer_relevance) as avg_answer_relevance,
  avg(faithfulness) as avg_faithfulness,
  avg(context_recall) as avg_context_recall,
  avg(tool_call_success_rate) as avg_tool_call_success_rate,
  avg(agent_task_success_rate) as avg_agent_task_success_rate
from evaluation_result
group by run_no, target_type
order by max(created_at) desc;
~~~

查看失败评测：

~~~sql
select
  run_no,
  target_type,
  target_id,
  status,
  error_message,
  input_summary,
  output_summary,
  created_at
from evaluation_result
where status <> 'success'
order by created_at desc
limit 20;
~~~

## 8. 内容资产：content_asset

用途：

- 查看生成内容
- 查看内容类型
- 查看业务对象
- 查看版本
- 查看审核状态
- 查看是否关联模型调用日志

查询最近内容资产：

~~~sql
select
  content_type,
  biz_type,
  biz_id,
  version,
  status,
  review_status,
  model_call_log_id,
  created_at
from content_asset
order by created_at desc
limit 20;
~~~

查看模型日志关联状态：

~~~sql
select
  content_type,
  biz_type,
  biz_id,
  status,
  review_status,
  model_call_log_id,
  metadata_json->>'model_call_log_link_status' as model_call_log_link_status,
  created_at
from content_asset
order by created_at desc
limit 20;
~~~

查看某个资产详情：

~~~sql
select
  id,
  asset_group_id,
  version,
  content_type,
  biz_type,
  biz_id,
  title,
  status,
  review_status,
  prompt_template_id,
  prompt_version_id,
  model_call_log_id,
  rule_check_result_json,
  metadata_json,
  created_at
from content_asset
where id = '替换为 content_asset.id';
~~~

## 9. 内容审核记录：content_review

用途：

- 查看系统规则审核
- 查看人工审核
- 查看审核意见
- 查看 request_id
- 查看审核流水

查询最近审核记录：

~~~sql
select
  review_type,
  review_status,
  reviewer_type,
  reviewer_id,
  comments,
  request_id,
  created_at
from content_review
order by created_at desc
limit 20;
~~~

按内容资产查询审核记录：

~~~sql
select
  review_type,
  review_status,
  reviewer_type,
  reviewer_id,
  sensitive_check_result_json,
  brand_check_result_json,
  model_review_result_json,
  comments,
  request_id,
  created_at
from content_review
where content_asset_id = '替换为 content_asset.id'
order by created_at asc;
~~~

## 10. 常用排查路径

### 10.1 排查一次客服 Agent 请求

推荐顺序：

1. 从 API 响应拿 request_id
2. 查 `agent_task`
3. 根据 `agent_task.id` 查 `agent_step_log`
4. 根据 `agent_task.id` 查 `tool_call_log`
5. 根据 request_id 查 `model_call_log`
6. 如果是政策问答，再查 `rag_retrieval_log`

### 10.2 排查一次 RAG 问答

推荐顺序：

1. 查 `rag_retrieval_log`
2. 查看 `retrieved_chunk_ids`
3. 查看 `retrieved_document_ids`
4. 查看 `scores_json`
5. 查 `model_call_log`
6. 检查 API 响应中的 `citations`

### 10.3 排查一次导购推荐

推荐顺序：

1. 查 `agent_task`，确认 `agent_type = shopping_guide`
2. 查 `tool_call_log`，确认 `tool_type = recommendation`
3. 查看工具是否包含 `parse_user_need` 和 `recall_product_candidates`
4. 检查响应中的 `recommendations` 和 `match_evidence`

### 10.4 排查一次运营 Copilot SQL 查询

推荐顺序：

1. 查 `agent_task`，确认 `agent_type = operation_copilot`
2. 查 `tool_call_log`，确认 `tool_type = bi`
3. 检查 SQL Guard 是否 passed
4. 检查 query_result 是否受 max_rows 限制

### 10.5 排查一次内容生成

推荐顺序：

1. 查 `content_asset`
2. 查 `content_review`
3. 根据 `model_call_log_id` 查 `model_call_log`
4. 查看 `prompt_template_id` 和 `prompt_version_id`
5. 查看 `rule_check_result_json`

### 10.6 排查一次评测执行

推荐顺序：

1. 查 `evaluation_result`
2. 按 `run_no` 聚合
3. 查看失败记录的 `error_message`
4. 查看 `metrics_json`
5. 如果是 RAG 评测，继续查 `rag_retrieval_log`
6. 如果是 Agent 评测，继续查 `agent_task` 和 `tool_call_log`

## 11. psql 快速查询方式

在项目根目录执行：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select provider, model_name, call_type, status, latency_ms, request_id, created_at from model_call_log order by created_at desc limit 10;"
~~~

RAG：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select query, retrieval_mode, result_count, latency_ms, request_id, created_at from rag_retrieval_log order by created_at desc limit 10;"
~~~

Agent：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select agent_type, task_no, intent, status, handoff_required, request_id, created_at from agent_task order by created_at desc limit 10;"
~~~

工具：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select tool_name, tool_type, status, latency_ms, created_at from tool_call_log order by created_at desc limit 10;"
~~~

评测：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select target_type, target_id, status, run_no, score, created_at from evaluation_result order by created_at desc limit 10;"
~~~

内容资产：

~~~powershell
docker compose exec postgres psql -U omni -d omni_ai -c "select content_type, biz_type, biz_id, version, status, review_status, model_call_log_id, created_at from content_asset order by created_at desc limit 10;"
~~~

## 12. asyncpg warning 说明

当前全量测试通过，但存在一个既有 warning：

~~~text
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
~~~

当前判断：

- 不影响全量测试通过
- 不影响 API 健康检查
- 不影响数据库迁移
- 不影响业务链路演示
- 可能来自测试环境中 asyncpg 连接资源释放时机

窗口 12 不为压 warning 大改业务主链。

后续可小范围排查：

- pytest fixture 是否正确释放资源
- httpx 测试调用是否存在未关闭连接
- SQLAlchemy AsyncSession 生命周期
- asyncpg 连接池关闭时机
- Windows / Conda 环境中的事件循环策略
