# 模块交接文档：执行窗口 2 - 核心数据模型

## 一、模块目标

本模块负责建立《智营 OmniCommerce AI：电商企业级大模型运营中台》的核心数据模型，为后续基础业务服务、模型网关、Prompt
管理、RAG、Agent、评测中心提供统一的数据结构基础。

本窗口只负责：

- 数据模型；
- Alembic 迁移；
- 核心验证种子数据；
- 数据模型说明。

本窗口不实现：

- 复杂业务接口；
- Agent；
- RAG 检索链路；
- 模型真实调用。

---

## 二、窗口识别结果

| 项目     | 内容                                 |
|--------|------------------------------------|
| 当前执行窗口 | 执行窗口 2                             |
| 当前窗口名称 | 核心数据模型                             |
| 本窗口目标  | 建立电商业务、大模型应用、Agent、RAG、评测所需的核心数据模型 |
| 上游依赖   | 执行窗口 1：基础工程骨架交接文档                  |

---

### 2.1 本窗口必须完成

- SQLAlchemy Model
- Alembic 迁移
- 核心验证种子数据方案
- 数据模型说明

---

### 2.2 本窗口禁止完成

- 复杂业务接口
- Agent
- RAG 检索链路
- 模型调用

---

### 2.3 最终交付物

```text
backend/app/models/*.py
backend/app/db/base.py 继承体系复用
backend/alembic/env.py 模型导入更新
Alembic migration 文件
核心验证种子数据脚本
Demo 场景种子数据脚本
本模块交接文档
```

---

### 2.4 验收标准

- 所有核心表模型存在；
- Alembic 迁移可执行；
- 表名和字段命名符合规范；
- 核心表包含 `tenant_id`；
- 核心业务表包含 `created_at / updated_at / deleted_at`；
- 日志类表包含 `request_id`；
- 有核心验证种子数据方案；
- 不破坏执行窗口 1 工程结构；
- 不引入 Java / Spring 技术栈。

---

## 三、已完成内容

本窗口已完成：

- SQLAlchemy 2.0 风格核心数据模型；
- 18 张核心表建模；
- 通用模型 Mixin：
    - UUID 主键；
    - 多租户字段；
    - 创建 / 更新时间；
    - 软删除字段；
    - `request_id` 日志追踪字段；
- Alembic 模型注册配置；
- Alembic 自动迁移文件生成；
- 数据库迁移执行；
- 核心验证种子数据脚本 `seed_core_data.py`；
- Demo 边界场景种子数据脚本 `seed_demo_scenarios.py`；
- 核心数据和 Demo 场景数据成功写入 PostgreSQL。

本窗口未实现：

- 复杂业务接口；
- Agent；
- RAG 检索链路；
- 模型真实调用；
- Java / Spring 技术栈。

---

## 四、新增文件清单

```text
backend/app/models/__init__.py
backend/app/models/mixins.py
backend/app/models/user.py
backend/app/models/product.py
backend/app/models/order.py
backend/app/models/ticket.py
backend/app/models/knowledge.py
backend/app/models/prompt.py
backend/app/models/llm.py
backend/app/models/agent.py
backend/app/models/evaluation.py
backend/alembic/versions/9c9c22e1cf47_create_core_data_models.py
backend/scripts/seed_core_data.py
backend/scripts/seed_demo_scenarios.py
docs/window2_handoff.md
```

---

## 五、修改文件清单

---

### 5.1 文件 1：`backend/alembic/env.py`

| 项目     | 内容                                                                      |
|--------|-------------------------------------------------------------------------|
| 修改内容   | 新增 `import app.models # noqa: F401`                                     |
| 修改原因   | 让 Alembic 在 autogenerate 时加载全部 SQLAlchemy 模型，使模型类注册进 `Base.metadata`    |
| 是否影响下游 | 是                                                                       |
| 影响说明   | 后续新增模型时，应继续通过 `backend/app/models/__init__.py` 统一导入，保证 Alembic 能检测到模型变更 |

---

### 5.2 文件 2：`backend/app/models/__init__.py`

| 项目     | 内容                                        |
|--------|-------------------------------------------|
| 修改内容   | 统一导入 18 张核心表对应的模型类                        |
| 修改原因   | 作为 SQLAlchemy 模型注册入口                      |
| 是否影响下游 | 是                                         |
| 影响说明   | 后续窗口新增模型时，必须在此文件补充导入，否则 Alembic 可能无法识别新增表 |

---

## 六、数据库变更

---

### 6.1 新增数据表

本窗口新增 18 张核心数据表：

```text
user_profile
product
product_sku
product_review
order_info
order_item
after_sale_ticket
customer_service_ticket
knowledge_document
knowledge_chunk
prompt_template
prompt_version
model_call_log
agent_task
agent_step_log
tool_call_log
evaluation_case
evaluation_result
```

---

### 6.2 修改数据表

无。

执行窗口 1 未创建业务表，本窗口不存在修改上游表结构的情况。

---

### 6.3 Alembic 迁移

新增迁移文件：

```text
backend/alembic/versions/9c9c22e1cf47_create_core_data_models.py
```

迁移验证结果：

```text
create_table: 18
drop_table: 18
alembic upgrade head: 成功
alembic current: 9c9c22e1cf47 (head)
```

---

### 6.4 核心表说明

| 表名                        | 说明                 | 类型                 |
|---------------------------|--------------------|--------------------|
| `user_profile`            | 用户画像表，支撑用户查询、客服、导购 | 业务表                |
| `product`                 | 商品 SPU 表           | 业务表                |
| `product_sku`             | 商品 SKU 表           | 业务表                |
| `product_review`          | 商品评价表              | 业务表                |
| `order_info`              | 订单主表               | 业务表                |
| `order_item`              | 订单明细表              | 业务表                |
| `after_sale_ticket`       | 售后单表               | 业务表                |
| `customer_service_ticket` | 客服工单表              | 业务表                |
| `knowledge_document`      | 知识库文档元数据表          | 业务表                |
| `knowledge_chunk`         | 知识库切片表             | 业务表                |
| `prompt_template`         | Prompt 模板表         | 业务表                |
| `prompt_version`          | Prompt 版本表         | 业务表                |
| `model_call_log`          | 模型调用日志表            | 日志表                |
| `agent_task`              | Agent 任务表          | 业务表，带 `request_id` |
| `agent_step_log`          | Agent 步骤日志表        | 日志表                |
| `tool_call_log`           | 工具调用日志表            | 日志表                |
| `evaluation_case`         | 评测用例表              | 业务表                |
| `evaluation_result`       | 评测结果表              | 日志表                |

---

### 6.5 通用字段说明

#### 业务表通用字段

| 字段名          | 类型       | 是否必填 | 说明    |
|--------------|----------|------|-------|
| `id`         | UUID     | 是    | 主键    |
| `tenant_id`  | UUID     | 是    | 租户 ID |
| `created_at` | DateTime | 是    | 创建时间  |
| `updated_at` | DateTime | 是    | 更新时间  |
| `deleted_at` | DateTime | 否    | 软删除时间 |

---

#### 日志表通用字段

| 字段名          | 类型       | 是否必填 | 说明      |
|--------------|----------|------|---------|
| `id`         | UUID     | 是    | 主键      |
| `tenant_id`  | UUID     | 是    | 租户 ID   |
| `request_id` | String   | 否    | 请求追踪 ID |
| `created_at` | DateTime | 是    | 创建时间    |

---

## 七、关键业务字段说明

---

### 7.1 `user_profile`

| 字段名               | 说明        |
|-------------------|-----------|
| `user_no`         | 用户业务编号    |
| `nickname`        | 用户昵称      |
| `phone_masked`    | 脱敏手机号     |
| `email_masked`    | 脱敏邮箱      |
| `member_level`    | 会员等级      |
| `preference_json` | 用户偏好 JSON |
| `tag_json`        | 用户标签 JSON |

---

### 7.2 `product`

| 字段名              | 说明        |
|------------------|-----------|
| `product_no`     | 商品业务编号    |
| `title`          | 商品标题      |
| `brand`          | 品牌        |
| `category`       | 类目        |
| `status`         | 商品状态      |
| `tag_json`       | 商品标签 JSON |
| `attribute_json` | 商品属性 JSON |

---

### 7.3 `product_sku`

| 字段名              | 说明       |
|------------------|----------|
| `product_id`     | 关联商品 ID  |
| `sku_no`         | SKU 业务编号 |
| `sku_name`       | SKU 名称   |
| `sale_price`     | 销售价      |
| `stock_quantity` | 库存数量     |
| `status`         | SKU 状态   |
| `spec_json`      | 规格 JSON  |

---

### 7.4 `order_info`

| 字段名                      | 说明      |
|--------------------------|---------|
| `order_no`               | 订单业务编号  |
| `user_id`                | 用户 ID   |
| `order_status`           | 订单状态    |
| `payment_status`         | 支付状态    |
| `fulfillment_status`     | 履约状态    |
| `total_amount`           | 订单原始总金额 |
| `paid_amount`            | 实付金额    |
| `receiver_snapshot_json` | 收货人脱敏快照 |

---

### 7.5 `order_item`

| 字段名           | 说明     |
|---------------|--------|
| `order_id`    | 订单 ID  |
| `product_id`  | 商品 ID  |
| `sku_id`      | SKU ID |
| `quantity`    | 购买数量   |
| `unit_price`  | 成交单价   |
| `paid_amount` | 明细实付金额 |
| `item_status` | 明细状态   |

---

### 7.6 `after_sale_ticket`

| 字段名               | 说明      |
|-------------------|---------|
| `ticket_no`       | 售后单编号   |
| `user_id`         | 用户 ID   |
| `order_id`        | 订单 ID   |
| `order_item_id`   | 订单明细 ID |
| `after_sale_type` | 售后类型    |
| `status`          | 售后状态    |
| `refund_amount`   | 退款金额    |
| `evidence_json`   | 凭证 JSON |

---

### 7.7 `customer_service_ticket`

| 字段名                     | 说明             |
|-------------------------|----------------|
| `ticket_no`             | 客服工单编号         |
| `user_id`               | 用户 ID          |
| `order_id`              | 关联订单 ID        |
| `source`                | 工单来源           |
| `category`              | 工单分类           |
| `priority`              | 优先级            |
| `status`                | 工单状态           |
| `related_agent_task_id` | 关联 Agent 任务 ID |

---

### 7.8 `knowledge_document`

| 字段名                  | 说明       |
|----------------------|----------|
| `document_no`        | 文档业务编号   |
| `title`              | 文档标题     |
| `source_type`        | 来源类型     |
| `storage_object_key` | 对象存储 Key |
| `status`             | 文档状态     |
| `parser_status`      | 解析状态     |
| `acl_json`           | 权限过滤元数据  |

---

### 7.9 `knowledge_chunk`

| 字段名                 | 说明       |
|---------------------|----------|
| `document_id`       | 文档 ID    |
| `chunk_no`          | 切片编号     |
| `content`           | 切片正文     |
| `page_no`           | 页码       |
| `section_title`     | 章节标题     |
| `keywords_json`     | 关键词 JSON |
| `embedding_id`      | 向量 ID    |
| `vector_collection` | 向量集合     |

---

### 7.10 `prompt_template`

| 字段名            | 说明        |
|----------------|-----------|
| `template_key` | 模板业务 Key  |
| `name`         | 模板名称      |
| `scene`        | Prompt 场景 |
| `status`       | 模板状态      |

---

### 7.11 `prompt_version`

| 字段名                    | 说明           |
|------------------------|--------------|
| `template_id`          | Prompt 模板 ID |
| `version`              | 版本号          |
| `content`              | Prompt 内容    |
| `variable_schema_json` | 变量 Schema    |
| `model_config_json`    | 推荐模型参数       |
| `gray_config_json`     | 灰度配置预留       |
| `is_active`            | 是否启用版本       |

---

### 7.12 `model_call_log`

| 字段名                  | 说明           |
|----------------------|--------------|
| `provider`           | 模型供应商        |
| `model_name`         | 模型名称         |
| `model_type`         | 模型类型         |
| `call_type`          | 调用类型         |
| `prompt_template_id` | Prompt 模板 ID |
| `prompt_version_id`  | Prompt 版本 ID |
| `input_tokens`       | 输入 token 数   |
| `output_tokens`      | 输出 token 数   |
| `cost_amount`        | 成本金额预留       |
| `latency_ms`         | 调用耗时         |
| `status`             | 调用状态         |

---

### 7.13 `agent_task`

| 字段名                | 说明       |
|--------------------|----------|
| `agent_type`       | Agent 类型 |
| `session_id`       | 会话 ID    |
| `task_no`          | 任务编号     |
| `input_summary`    | 输入摘要     |
| `output_summary`   | 输出摘要     |
| `status`           | 任务状态     |
| `intent`           | 意图       |
| `handoff_required` | 是否转人工    |

---

### 7.14 `agent_step_log`

| 字段名              | 说明          |
|------------------|-------------|
| `agent_task_id`  | Agent 任务 ID |
| `step_name`      | 步骤名称        |
| `step_order`     | 步骤顺序        |
| `input_summary`  | 输入摘要        |
| `output_summary` | 返回摘要        |
| `status`         | 步骤状态        |
| `latency_ms`     | 步骤耗时        |

---

### 7.15 `tool_call_log`

| 字段名                 | 说明            |
|---------------------|---------------|
| `agent_task_id`     | Agent 任务 ID   |
| `agent_step_log_id` | Agent 步骤日志 ID |
| `tool_name`         | 工具名称          |
| `tool_type`         | 工具类型          |
| `input_summary`     | 入参摘要          |
| `output_summary`    | 返回摘要          |
| `status`            | 调用状态          |
| `latency_ms`        | 调用耗时          |

---

### 7.16 `evaluation_case`

| 字段名                      | 说明         |
|--------------------------|------------|
| `case_no`                | 评测用例编号     |
| `case_type`              | 用例类型       |
| `name`                   | 用例名称       |
| `input_json`             | 输入 JSON    |
| `expected_output_json`   | 期望输出 JSON  |
| `reference_context_json` | 参考上下文 JSON |
| `status`                 | 用例状态       |

---

### 7.17 `evaluation_result`

| 字段名                       | 说明        |
|---------------------------|-----------|
| `case_id`                 | 评测用例 ID   |
| `run_no`                  | 运行批次编号    |
| `target_type`             | 评测目标类型    |
| `target_id`               | 评测目标 ID   |
| `score`                   | 综合得分      |
| `answer_relevance`        | 答案相关性     |
| `faithfulness`            | 忠实度       |
| `context_recall`          | 上下文召回     |
| `context_precision`       | 上下文精确率    |
| `tool_call_success_rate`  | 工具调用成功率   |
| `agent_task_success_rate` | Agent 成功率 |
| `latency_ms`              | 耗时        |
| `token_cost`              | Token 成本  |

---

## 八、API 接口清单

本窗口未新增 API。

说明：

- 执行窗口 2 只负责核心数据模型、迁移和种子数据；
- 基础业务接口由执行窗口 3 实现；
- 模型网关接口由执行窗口 4 实现；
- Prompt 管理接口由执行窗口 5 实现；
- RAG、Agent、评测接口由后续窗口实现。

---

## 九、配置项说明

本窗口未新增新的环境变量。

继续沿用执行窗口 1 的配置项：

| 配置项            | 说明                | 是否必填 | 默认值                                                              |
|----------------|-------------------|------|------------------------------------------------------------------|
| `DATABASE_URL` | PostgreSQL 异步连接地址 | 是    | `postgresql+asyncpg://omni:omni_password@localhost:5432/omni_ai` |
| `REDIS_URL`    | Redis 连接地址        | 是    | `redis://localhost:6379/0`                                       |
| `APP_NAME`     | 应用名称              | 否    | `omni-commerce-ai`                                               |
| `APP_ENV`      | 运行环境              | 否    | `dev`                                                            |
| `APP_DEBUG`    | 是否开启调试配置          | 否    | `true`                                                           |
| `LOG_LEVEL`    | 日志级别              | 否    | `INFO`                                                           |

---

## 十、运行方式

---

### 10.1 启动基础服务

在项目根目录执行：

```bash
docker compose up -d
```

检查服务状态：

```bash
docker compose ps
```

预期：

```text
omni_backend    Up
omni_postgres   Up (healthy)
omni_redis      Up (healthy)
```

---

### 10.2 激活虚拟环境

在 `backend` 目录执行：

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### 10.3 执行数据库迁移

在 `backend` 目录执行：

```bash
python -m alembic upgrade head
```

---

### 10.4 查看当前迁移版本

```bash
python -m alembic current
```

预期：

```text
9c9c22e1cf47 (head)
```

---

### 10.5 初始化核心验证种子数据

```bash
python scripts/seed_core_data.py
```

---

### 10.6 初始化 Demo 场景种子数据

```bash
python scripts/seed_demo_scenarios.py
```

---

## 十一、测试方式

---

### 11.1 模型注册检查

在 `backend` 目录执行：

```bash
python -c "import app.models; from app.db.base import Base; print(sorted(Base.metadata.tables.keys()))"
```

预期包含 18 张表：

```text
after_sale_ticket
agent_step_log
agent_task
customer_service_ticket
evaluation_case
evaluation_result
knowledge_chunk
knowledge_document
model_call_log
order_info
order_item
product
product_review
product_sku
prompt_template
prompt_version
tool_call_log
user_profile
```

---

### 11.2 SQLAlchemy 映射检查

```bash
python -c "import app.models; from sqlalchemy.orm import configure_mappers; configure_mappers(); from app.db.base import Base; print(len(Base.metadata.tables)); print(sorted(Base.metadata.tables.keys()))"
```

预期：

```text
18
```

---

### 11.3 Alembic migration 检查

```bash
python -c "from pathlib import Path; p=Path('alembic/versions/9c9c22e1cf47_create_core_data_models.py'); s=p.read_text(encoding='utf-8'); print('create_table:', s.count('op.create_table')); print('drop_table:', s.count('op.drop_table'))"
```

预期：

```text
create_table: 18
drop_table: 18
```

---

### 11.4 Migration 语法检查

```bash
python -m py_compile alembic/versions/9c9c22e1cf47_create_core_data_models.py
```

无输出即通过。

---

### 11.5 执行迁移

```bash
python -m alembic upgrade head
python -m alembic current
```

预期：

```text
9c9c22e1cf47 (head)
```

---

### 11.6 核心验证种子数据检查

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select count(*) from user_profile;"
docker compose exec postgres psql -U omni -d omni_ai -c "select count(*) from product;"
docker compose exec postgres psql -U omni -d omni_ai -c "select count(*) from order_info;"
docker compose exec postgres psql -U omni -d omni_ai -c "select count(*) from knowledge_document;"
docker compose exec postgres psql -U omni -d omni_ai -c "select count(*) from prompt_template;"
docker compose exec postgres psql -U omni -d omni_ai -c "select count(*) from evaluation_case;"
```

---

### 11.7 Demo 场景数据检查

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select user_no, member_level from user_profile order by user_no;"
docker compose exec postgres psql -U omni -d omni_ai -c "select product_no, title, status from product order by product_no;"
docker compose exec postgres psql -U omni -d omni_ai -c "select sku_no, stock_quantity, status from product_sku order by sku_no;"
docker compose exec postgres psql -U omni -d omni_ai -c "select order_no, order_status, payment_status, fulfillment_status from order_info order by order_no;"
docker compose exec postgres psql -U omni -d omni_ai -c "select ticket_no, after_sale_type, status from after_sale_ticket order by ticket_no;"
docker compose exec postgres psql -U omni -d omni_ai -c "select rating, sentiment, content from product_review order by rating;"
```

已验证结果：

#### `user_profile`

```text
U100001 | gold
U200001 | normal
```

#### `product`

```text
P100001 | 智营智能恒温电热水壶 | active
P200001 | 已下架智能香薰机     | inactive
P200002 | 低库存蓝牙降噪耳机   | active
```

#### `product_sku`

```text
SKU100001 | 100 | active
SKU200001 | 20  | inactive
SKU200002 | 2   | active
```

#### `order_info`

```text
O100001 | completed | paid | delivered
O200001 | paid      | paid | unfulfilled
```

#### `after_sale_ticket`

```text
AS100001 | refund | pending
AS200001 | refund | pending
AS200002 | refund | approved
AS200003 | return | rejected
AS200004 | refund | completed
```

#### `product_review`

```text
2 | negative | 耳机降噪效果没有预期好，佩戴时间长了有点不舒服。
5 | positive | 控温很方便，烧水速度也不错，客服响应很快。
```

---

## 十二、局部实现决策

---

### 决策 1：使用 Mixin 统一核心字段

| 项目      | 内容                                                                                          |
|---------|---------------------------------------------------------------------------------------------|
| 决策内容    | 通过 `BusinessBaseMixin`、`LogBaseMixin`、`RequestIdMixin` 统一业务表和日志表字段                          |
| 决策原因    | 避免 18 张表重复定义 `id` / `tenant_id` / `created_at` / `updated_at` / `deleted_at` / `request_id` |
| 影响范围    | 影响所有执行窗口 2 新增模型                                                                             |
| 后续可调整方式 | 后续如需新增公共字段，应先评估是否属于全局模型合同，必要时回总控确认                                                          |

---

### 决策 2：业务表默认支持软删除

| 项目      | 内容                                          |
|---------|---------------------------------------------|
| 决策内容    | 业务表默认包含 `deleted_at`                        |
| 决策原因    | 符合项目全局数据库规范，避免核心业务数据被物理删除                   |
| 影响范围    | 用户、商品、订单、售后、工单、知识库、Prompt、评测用例等业务表          |
| 后续可调整方式 | 后续 repository 查询时应默认过滤 `deleted_at is null` |

---

### 决策 3：日志类表不设计 `updated_at / deleted_at`

| 项目      | 内容                                                                                                        |
|---------|-----------------------------------------------------------------------------------------------------------|
| 决策内容    | 日志类表使用 `LogBaseMixin`，包含 `id` / `tenant_id` / `request_id` / `created_at`，不包含 `updated_at` / `deleted_at` |
| 决策原因    | 日志类表偏审计记录，不建议被业务更新或软删除                                                                                    |
| 影响范围    | `model_call_log`、`agent_step_log`、`tool_call_log`、`evaluation_result`                                     |
| 后续可调整方式 | 如总控要求日志表也支持软删除，可在后续迁移中统一补充                                                                                |

---

### 决策 4：金额字段统一使用 Numeric

| 项目      | 内容                                 |
|---------|------------------------------------|
| 决策内容    | 价格、金额、成本、退款金额、Token 成本使用 `Numeric` |
| 决策原因    | 避免浮点精度问题                           |
| 影响范围    | 商品、订单、售后、模型调用日志、评测结果               |
| 后续可调整方式 | 后续业务层使用 `Decimal` 处理金额             |

---

### 决策 5：JSON 扩展字段统一使用 PostgreSQL JSONB

| 项目      | 内容                                |
|---------|-----------------------------------|
| 决策内容    | 偏好、标签、规格、快照、元数据、评测指标等使用 `JSONB`   |
| 决策原因    | 适合 PostgreSQL，并为后续复杂场景保留扩展能力      |
| 影响范围    | 用户画像、商品、订单、知识库、Prompt、日志、评测       |
| 后续可调整方式 | 如某些 JSON 字段成为高频查询条件，可补充表达式索引或拆分字段 |

---

### 决策 6：Prompt 模型只做模板与版本，不做 Prompt 服务

| 项目      | 内容                                            |
|---------|-----------------------------------------------|
| 决策内容    | 本窗口仅创建 `prompt_template` 和 `prompt_version` 表 |
| 决策原因    | Prompt CRUD、变量渲染和版本启停属于执行窗口 5                 |
| 影响范围    | 后续 Prompt 管理模块可直接基于当前表实现                      |
| 后续可调整方式 | 执行窗口 5 可补充服务层、接口层和默认 Prompt 数据                |

---

### 决策 7：Agent 相关表只做日志与任务结构，不做 Agent 编排

| 项目      | 内容                                                   |
|---------|------------------------------------------------------|
| 决策内容    | 本窗口仅创建 `agent_task`、`agent_step_log`、`tool_call_log` |
| 决策原因    | LangGraph 工作流和工具调用属于执行窗口 7 之后                        |
| 影响范围    | 后续客服 Agent、导购 Agent、BI Agent 可复用这些日志表                |
| 后续可调整方式 | 后续如需修改 Agent 状态结构，应回总控确认                             |

---

### 决策 8：种子数据拆分为核心验证与 Demo 场景

| 项目      | 内容                                                           |
|---------|--------------------------------------------------------------|
| 决策内容    | `seed_core_data.py` 覆盖核心业务链路，`seed_demo_scenarios.py` 覆盖边界场景 |
| 决策原因    | 核心链路和边界场景分开维护，避免基础种子数据臃肿                                     |
| 影响范围    | 执行窗口 3 的基础业务服务测试、后续 Agent / RAG / 评测演示                       |
| 后续可调整方式 | 后续窗口可按模块新增独立 seed 脚本                                         |

---

### 决策 9：种子脚本采用严格幂等检查

| 项目      | 内容                                           |
|---------|----------------------------------------------|
| 决策内容    | 种子脚本检查多张关键表。全部存在则跳过，全部不存在则插入，部分存在则报错         |
| 决策原因    | 避免部分写入失败后重跑时直接跳过，导致数据库处于半残状态                 |
| 影响范围    | `seed_core_data.py`、`seed_demo_scenarios.py` |
| 后续可调整方式 | 如后续需要更强修复能力，可增加清理脚本或 upsert 策略               |

---

## 十三、已知问题

当前已知问题如下：

1. 当前未实现 repository 层默认过滤 `deleted_at is null`，该能力应由执行窗口 3 在数据访问层实现；
2. 当前 `assigned_operator_id` 暂用字符串预留，完整用户认证和 RBAC 尚未实现；
3. 当前 `model_call_log` 仅建表和种子日志，不做真实模型调用，真实调用由执行窗口 4 完成；
4. 当前 `prompt_template` / `prompt_version` 只完成数据模型，不实现 Prompt CRUD 和渲染，后续由执行窗口 5 完成；
5. 当前 `knowledge_document` / `knowledge_chunk` 只完成数据模型，不实现文档上传、切片、向量化和检索，后续由执行窗口 6 完成；
6. 当前 `agent_task` / `agent_step_log` / `tool_call_log` 只完成数据结构，不实现 LangGraph Agent，后续由执行窗口 7 之后完成；
7. 当前种子脚本在检测到部分数据已存在时会主动报错，需要人工清理半残种子数据后重跑；这是为了避免自动补缺造成外键链路不一致。

---

## 十四、需总控确认事项

暂无需总控确认事项。

说明：

- 本窗口未修改全局技术栈；
- 未修改执行窗口 1 的统一响应、异常处理、`request_id` 中间件；
- 未修改已有 API 合同；
- 未新增跨模块公共中间件；
- 未引入 Java / Spring；
- 所有新增表均属于执行窗口 2 任务范围内要求的核心表。

---

## 十五、给下一个执行窗口的注意事项

执行窗口 3 是“基础业务服务”，接手时请注意：

1. 所有数据库查询应通过 repository 层实现，不要把查询写进 API 层；
2. service 层应复用当前 18 张核心表，不要重复建业务表；
3. 查询业务表时应默认过滤 `deleted_at is null`；
4. 基础业务接口应覆盖：
    - 用户画像查询；
    - 商品列表查询；
    - 商品详情查询；
    - SKU 查询；
    - 商品评价查询；
    - 订单查询；
    - 订单详情查询；
    - 售后单创建；
    - 售后单查询；
    - 客服工单创建；
    - 客服工单查询；
5. 商品查询应注意 `product.status` 和 `product_sku.status`：
    - Demo 数据包含 `inactive` 商品和 `inactive` SKU；
6. SKU 查询应注意库存：
    - Demo 数据包含低库存 SKU：`SKU200002`，库存为 `2`；
7. 订单查询应注意不同履约状态：
    - `O100001`：已完成、已送达；
    - `O200001`：已支付、待发货；
8. 售后查询应注意多状态：
    - `pending`
    - `approved`
    - `rejected`
    - `completed`
9. 商品评价查询应注意情感倾向：
    - `positive`
    - `negative`
10. 不要在执行窗口 3 直接实现 Agent 工具，Agent 工具属于后续窗口；
11. 不要在执行窗口 3 直接调用模型 API；
12. 不要绕过统一响应格式；
13. 不要引入 Java / Spring 技术栈。

---

## 十六、一句话交接总结

执行窗口 2 已完成智营 OmniCommerce AI 的核心数据模型建设，建立了 18 张核心表、通用 Mixin、Alembic 迁移、核心种子数据和 Demo
场景数据。

执行窗口 3 可以在此基础上进入基础业务服务开发，但必须坚持：

```text
repository 负责数据访问
service 负责业务逻辑
api 负责接口暴露
不要越界实现 Agent / RAG / 模型调用
```