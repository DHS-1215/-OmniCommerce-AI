# 执行窗口 5：Prompt 管理模块交接文档

## 一、窗口基本信息

| 项目   | 内容                           |
|------|------------------------------|
| 执行窗口 | 执行窗口 5                       |
| 模块名称 | Prompt 管理                    |
| 当前状态 | 已完成                          |
| 验收结果 | Docker 容器内全量测试通过，`48 passed` |

本窗口在已有 `prompt_template`、`prompt_version` 数据模型基础上，完成了：

- Prompt 模板管理；
- Prompt 版本管理；
- 场景分类；
- 启用 / 停用；
- 变量渲染；
- 灰度字段预留；
- 默认 Prompt 种子数据；
- API 验证能力。

---

## 二、本窗口完成目标

本窗口完成了以下能力：

- Prompt 模板 CRUD；
- Prompt 版本管理；
- Prompt 场景分类 `scene`；
- Prompt 启用 / 停用；
- Prompt 变量渲染；
- 按 `template_key` 获取当前启用版本；
- 按 `scene` 获取当前启用版本；
- 灰度字段 `gray_config_json` 预留；
- 模型参数 `model_config_json` 预留；
- Prompt 调用追踪字段输出 `template_id` / `version_id`；
- 默认 Prompt 种子数据；
- Prompt API 自动化测试；
- Prompt Service 自动化测试。

本窗口没有越权实现：

- 未实现具体 Agent；
- 未实现 RAG 主流程；
- 未绕过模型网关调用模型；
- 未把 Prompt 硬编码到业务模块；
- 未新增数据库表；
- 未修改全局响应协议；
- 未修改全局异常体系。

---

## 三、新增 / 修改文件清单

### 3.1 新增文件

```text
backend/app/schemas/prompt.py
backend/app/prompts/renderer.py
backend/app/repositories/prompt_repository.py
backend/app/services/prompt_service.py
backend/app/api/v1/prompts.py
backend/scripts/seed_prompt_data.py
backend/tests/test_prompt_service.py
backend/tests/test_prompt_api.py
```

---

### 3.2 修改文件

```text
backend/app/api/v1/router.py
```

修改内容：

```python
from app.api.v1.prompts import router as prompts_router

api_v1_router.include_router(
    prompts_router,
    prefix="/prompts",
    tags=["prompts"],
)
```

---

## 四、数据库变更

本窗口没有新增数据库表，也没有新增 Alembic 迁移。

直接复用执行窗口 2 已完成的两张表：

```text
prompt_template
prompt_version
```

---

### 4.1 使用到的核心字段

#### `prompt_template`

```text
id
tenant_id
template_key
name
scene
description
status
metadata_json
created_at
updated_at
deleted_at
```

#### `prompt_version`

```text
id
tenant_id
template_id
version
content
variable_schema_json
model_config_json
gray_config_json
is_active
status
change_log
created_at
updated_at
deleted_at
```

---

### 4.2 版本启用规则

本窗口定义并实现了以下规则：

> 同一个 Prompt 模板下，同一时间只能有一个 `is_active=true` 且 `status=active` 的版本。

启用新版本时：

1. 先将同模板下旧 active 版本设置为 inactive；
2. 再将目标版本设置为 active。

---

## 五、模块设计说明

---

### 5.1 `schemas/prompt.py`

作用：

> 定义 Prompt 管理模块的请求体和响应体。

主要包含：

```text
PromptTemplateCreate
PromptTemplateUpdate
PromptTemplateResponse
PromptTemplateDetailResponse

PromptVersionCreate
PromptVersionUpdate
PromptVersionResponse

PromptActiveVersionResponse
PromptRenderRequest
PromptRenderResponse
```

为什么写这个模块：

> Schema 是 API、Service、测试之间的接口合同。  
> 它明确了创建模板需要什么字段、创建版本需要什么字段、渲染 Prompt 需要什么变量、接口返回什么结构。

如果没有这个模块，API 层、Service 层、测试层会各自拼字段，后面维护会很乱。

---

### 5.2 `prompts/renderer.py`

作用：

> 负责 Prompt 变量渲染。

支持变量格式：

```text
{{variable_name}}
{{ variable_name }}
```

示例：

```text
你好，{{user_name}}，你的订单是 {{order_no}}
```

传入：

```json
{
  "user_name": "张三",
  "order_no": "O100001"
}
```

渲染后：

```text
你好，张三，你的订单是 O100001
```

同时支持变量校验：

```json
{
  "required": [
    "user_message",
    "conversation_summary"
  ],
  "properties": {
    "user_message": {
      "type": "string",
      "required": true
    }
  }
}
```

如果缺少必填变量，会抛出：

```text
PROMPT_RENDER_VARIABLE_MISSING
```

为什么写这个模块：

> Prompt 管理不能只是把提示词存数据库。  
> 真正可用的 Prompt 管理必须支持“模板 + 变量 = 可调用 Prompt”。

这个模块不查数据库、不调用模型，只负责渲染，边界清楚。

---

### 5.3 `repositories/prompt_repository.py`

作用：

> 负责 Prompt 相关数据库访问。

主要能力：

```text
list_templates
get_template_by_id
get_template_by_key
create_template
update_template
soft_delete_template

list_versions
get_version_by_id
get_version_by_number
get_next_version_number
create_version
update_version
deactivate_versions_by_template_id
activate_version
deactivate_version

get_active_version_by_template_id
get_active_version_by_template_key
get_active_version_by_scene
```

为什么写这个模块：

> Repository 统一封装数据库查询，避免 API 或 Service 到处拼 SQL。

所有查询默认遵守：

```text
tenant_id 隔离
deleted_at is null 软删除过滤
```

---

### 5.4 `services/prompt_service.py`

作用：

> 负责 Prompt 业务规则。

主要能力：

```text
创建 Prompt 模板
更新 Prompt 模板
停用 Prompt 模板
归档 Prompt 模板
创建 Prompt 版本
更新 Prompt 版本
启用 Prompt 版本
停用 Prompt 版本
按 template_key 获取启用版本
按 scene 获取启用版本
渲染 Prompt
```

为什么写这个模块：

> Service 是业务规则中心。

例如：

- 同一个模板只能有一个启用版本；
- 启用新版本前要停用旧版本；
- 缺变量要抛业务异常。

这些都不应该写在 API 层或 Repository 层。

---

### 5.5 `api/v1/prompts.py`

作用：

> 暴露 Prompt 管理 HTTP API。

API 层只负责：

- 接收请求；
- 调用 `PromptService`；
- 返回统一响应。

不负责：

- 不写 SQL；
- 不写复杂业务规则；
- 不调用模型网关；
- 不做 Agent / RAG。

---

### 5.6 `scripts/seed_prompt_data.py`

作用：

> 写入默认 Prompt 种子数据。

默认写入 8 个场景：

```text
customer_service_intent
customer_service_answer
rag_answer_generation
shopping_guide_recommendation
text_to_sql
operation_report_generation
content_generation
content_review
```

为什么写这个模块：

> 后续窗口 6 / 7 / 8 / 9 / 10 需要直接读取默认 Prompt。  
> 如果没有种子数据，后续模块还得手工造 Prompt，交接成本高。

种子脚本是幂等的：

```text
模板不存在：创建模板 + v1 active 版本
模板存在且已有 active 版本：跳过
模板存在但没有 active 版本：补 active 版本
```

---

## 六、API 清单

---

### 6.1 Prompt 模板接口

#### 查询 Prompt 模板列表

```http
GET /api/v1/prompts
```

查询参数：

```text
tenant_id
page
page_size
scene
status
keyword
```

示例：

```bash
curl.exe "http://127.0.0.1:8002/api/v1/prompts?tenant_id=00000000-0000-0000-0000-000000000001"
```

---

#### 创建 Prompt 模板

```http
POST /api/v1/prompts
```

请求体示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "template_key": "cs_answer_default",
  "name": "客服回答生成默认 Prompt",
  "scene": "customer_service_answer",
  "description": "用于客服 Agent 生成用户回复",
  "metadata_json": {
    "owner": "customer_service"
  }
}
```

---

#### 查询 Prompt 模板详情

```http
GET /api/v1/prompts/{template_id}
```

---

#### 更新 Prompt 模板

```http
PATCH /api/v1/prompts/{template_id}
```

---

#### 停用 Prompt 模板

```http
POST /api/v1/prompts/{template_id}/deactivate
```

---

#### 归档 Prompt 模板

```http
DELETE /api/v1/prompts/{template_id}
```

说明：

> 归档使用软删除，不物理删除数据库记录。

---

### 6.2 Prompt 版本接口

#### 查询模板版本列表

```http
GET /api/v1/prompts/{template_id}/versions
```

---

#### 创建 Prompt 版本

```http
POST /api/v1/prompts/{template_id}/versions
```

请求体示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "content": "用户问题：{{user_question}}",
  "variable_schema_json": {
    "required": [
      "user_question"
    ],
    "properties": {
      "user_question": {
        "type": "string",
        "required": true
      }
    }
  },
  "model_config_json": {
    "provider": "mock",
    "model": "mock-chat-model",
    "temperature": 0.2
  },
  "gray_config_json": {
    "enabled": false
  },
  "is_active": true,
  "change_log": "初始版本"
}
```

---

#### 查询 Prompt 版本详情

```http
GET /api/v1/prompts/versions/{version_id}
```

---

#### 更新 Prompt 版本

```http
PATCH /api/v1/prompts/versions/{version_id}
```

说明：

> 不允许通过 update 接口直接激活版本。  
> 激活版本必须调用 activate 接口，避免破坏“同模板单 active 版本”规则。

---

#### 启用 Prompt 版本

```http
POST /api/v1/prompts/versions/{version_id}/activate
```

---

#### 停用 Prompt 版本

```http
POST /api/v1/prompts/versions/{version_id}/deactivate
```

---

### 6.3 启用版本查询接口

#### 按 `template_key` 获取当前启用版本

```http
GET /api/v1/prompts/by-template-key/{template_key}/active
```

---

#### 按 `scene` 获取当前启用版本

```http
GET /api/v1/prompts/by-scene/{scene}/active
```

示例：

```bash
curl.exe "http://127.0.0.1:8002/api/v1/prompts/by-scene/customer_service_intent/active?tenant_id=00000000-0000-0000-0000-000000000001"
```

---

### 6.4 Prompt 渲染接口

```http
POST /api/v1/prompts/render
```

请求体示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "scene": "customer_service_intent",
  "variables": {
    "user_message": "我的订单什么时候发货？",
    "conversation_summary": ""
  }
}
```

返回关键字段：

```text
template_id
version_id
template_key
scene
version
rendered_content
variables
model_config_json
gray_config_json
```

为什么返回 `template_id` 和 `version_id`：

> 后续模型调用可以把这两个字段传给 ModelGateway，写入 `model_call_log`，实现 Prompt 调用追踪。

---

## 七、默认 Prompt 种子数据

本窗口默认写入以下 Prompt：

| `template_key`                          | `scene`                         | 说明          |
|-----------------------------------------|---------------------------------|-------------|
| `cs_intent_default`                     | `customer_service_intent`       | 客服意图识别      |
| `cs_answer_default`                     | `customer_service_answer`       | 客服回答生成      |
| `rag_answer_generation_default`         | `rag_answer_generation`         | RAG 回答生成    |
| `shopping_guide_recommendation_default` | `shopping_guide_recommendation` | 智能导购推荐      |
| `text_to_sql_default`                   | `text_to_sql`                   | Text-to-SQL |
| `operation_report_generation_default`   | `operation_report_generation`   | 运营报告生成      |
| `content_generation_default`            | `content_generation`            | 内容生成        |
| `content_review_default`                | `content_review`                | 内容审核        |

运行方式：

```bash
cd D:\omni-commerce-ai\backend
python scripts/seed_prompt_data.py
```

Docker 容器内运行：

```bash
docker compose exec backend python scripts/seed_prompt_data.py
```

---

## 八、验证方式与结果

### 8.1 手工 curl 验证

已验证：

```text
GET /api/v1/prompts
GET /api/v1/prompts/by-scene/customer_service_intent/active
POST /api/v1/prompts/render
缺变量异常 PROMPT_RENDER_VARIABLE_MISSING
```

---

### 8.2 自动化测试

新增测试文件：

```text
tests/test_prompt_service.py
tests/test_prompt_api.py
```

测试内容：

```text
PromptService 创建模板
PromptService 创建版本
PromptService 渲染 Prompt
PromptService 缺变量异常

Prompt API 查询模板列表
Prompt API 按 scene 获取启用版本
Prompt API 渲染成功
Prompt API 缺变量异常
```

---

### 8.3 最终全量测试结果

Docker 容器内执行：

```bash
docker compose exec backend python -m pytest tests/
```

最终结果：

```text
48 passed in 3.66s
```

说明：

- 窗口 5 自身测试通过；
- 窗口 5 没有破坏原有 products / orders / aftersales / tickets / llm 等模块。

---

## 九、局部实现决策

---

### 9.1 `scene` 不做唯一约束

当前实现允许同一租户下同一个 `scene` 存在多个 Prompt 模板。

原因：

- 窗口 2 的表结构只对 `tenant_id + template_key` 做了唯一约束；
- 没有对 `tenant_id + scene` 做唯一约束；
- 窗口 5 不擅自修改数据库结构。

当前按 `scene` 查询 active Prompt 时：

> 取该 scene 下最新创建的 active 模板及其 active 版本。

如果后续总控要求一个 `scene` 只能有一个模板，需要新增唯一约束或业务校验。

---

### 9.2 Prompt 版本号自动递增

创建新版本时，不允许调用方手动传版本号。

规则：

```text
next_version = max(version) + 1
```

原因：

- 避免版本号冲突；
- 避免版本号倒退；
- 便于审计和回滚。

---

### 9.3 不允许通过 `update_version` 直接激活版本

激活版本必须调用：

```http
POST /api/v1/prompts/versions/{version_id}/activate
```

原因：

> 激活版本不是简单修改 `status`。  
> 还必须停用同模板下旧 active 版本。

---

### 9.4 Prompt 渲染不调用模型

`render_prompt` 只负责返回：

```text
rendered_content
template_id
version_id
model_config_json
gray_config_json
```

不调用模型网关。

原因：

- 窗口 5 的职责是 Prompt 管理；
- 模型调用必须交给窗口 4 的 `ModelGateway`。

---

## 十、已知问题 / 注意事项

### 10.1 历史种子数据已软归档

数据库中曾存在旧模板：

```text
template_key = customer_service_intent
scene = customer_service_intent
```

为避免与新默认模板 `cs_intent_default` 产生 scene 查询歧义，已处理为：

```text
status = archived
deleted_at = now()
对应版本 status = inactive
is_active = false
```

没有物理删除，符合软删除规范。

---

### 10.2 API 测试风格统一为请求运行中服务

Prompt API 测试最初使用 `TestClient(app)`，在全量测试中与 `asyncpg` 连接池出现事件循环冲突。

最终已调整为和现有业务 API 测试一致：

```text
使用 httpx 请求运行中的 backend 服务
默认 BASE_URL = http://127.0.0.1:8000
宿主机可通过 TEST_API_BASE_URL 覆盖
```

这样 Docker 容器内全量测试已稳定通过。

---

## 十一、给下游窗口的注意事项

---

### 11.1 给窗口 6：RAG

RAG 回答生成不要硬编码 Prompt。

应通过：

```text
scene = rag_answer_generation
```

获取当前启用 Prompt，然后调用渲染接口或 service。

建议变量：

```text
question
context
citation_rules
```

渲染后再交给模型网关。

---

### 11.2 给窗口 7：客服 Agent

客服 Agent 至少可以使用两个 scene：

```text
customer_service_intent
customer_service_answer
```

建议流程：

1. 使用 `customer_service_intent` 做意图识别；
2. 根据意图调用订单 / 售后 / 工单 / 知识库工具；
3. 使用 `customer_service_answer` 生成最终用户回复；
4. 调用 ModelGateway 时记录 `prompt_template_id` / `prompt_version_id`。

---

### 11.3 给窗口 8：智能导购 Agent

导购推荐使用：

```text
shopping_guide_recommendation
```

需要传入变量：

```text
user_need
budget
user_preference
candidate_products
```

---

### 11.4 给窗口 9：BI Agent

BI / 运营 Copilot 可使用：

```text
text_to_sql
operation_report_generation
```

注意：

> `text_to_sql` 默认 Prompt 已限制只能生成 `SELECT` 查询。  
> 后续仍需要在 SQL 执行层做二次安全校验，不能只依赖 Prompt。

---

### 11.5 给窗口 10：内容生成

内容生成和审核可使用：

```text
content_generation
content_review
```

建议：

> 内容生成后必须经过内容审核 Prompt 或规则审核再出结果。

---

## 十二、运行命令汇总

### 12.1 运行种子数据

```bash
cd D:\omni-commerce-ai\backend
python scripts/seed_prompt_data.py
```

---

### 12.2 重建后端容器

```bash
cd D:\omni-commerce-ai
docker compose up -d --build backend
```

---

### 12.3 运行 Prompt 测试

```bash
docker compose exec backend python -m pytest tests/test_prompt_service.py tests/test_prompt_api.py
```

---

### 12.4 运行全量测试

```bash
docker compose exec backend python -m pytest tests/
```

---

## 十三、本窗口交付结论

| 项目         | 结果                   |
|------------|----------------------|
| 自评状态       | 已完成                  |
| 是否建议进入下一窗口 | 是                    |
| 建议进入       | 执行窗口 6：RAG / 知识库模块   |
| 最终全量测试     | `48 passed in 3.66s` |

原因说明：

- 已完成 Prompt 模板管理；
- 已完成 Prompt 版本管理；
- 已完成变量渲染；
- 已完成默认 Prompt 种子数据；
- 已完成 Prompt API；
- 已完成 Prompt Service / API 自动化测试；
- 未绕过模型网关；
- 未越权实现 RAG / Agent；
- 未新增数据库表；
- 未修改全局响应协议和异常体系。

---

## 十四、一句话交接总结

执行窗口 5 已完成智营 OmniCommerce AI 的 Prompt 管理模块，形成：

```text
Prompt 模板
Prompt 版本
场景分类
启用 / 停用
变量渲染
默认种子数据
Prompt 调用追踪字段
```

后续 RAG、Agent、导购、BI、内容生成模块都应通过 Prompt 管理模块获取和渲染 Prompt，再交给模型网关调用模型。