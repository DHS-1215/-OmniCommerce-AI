# 窗口 13 交接文档：v1.1 认证 / RBAC / 租户隔离轻量生产化增强

## 1. 窗口目标

窗口 13 在 v1.0 已稳定通过验收的基础上，补充轻量生产化身份体系，不重构原有 RAG、Agent、内容生成、评测中心和模型网关主链路。

本窗口目标：

- 补充轻量认证体系；
- 支持 JWT 登录态；
- 新增 current_user / current_tenant 上下文解析；
- 支持 admin / operator / viewer 三类角色；
- 新增 `require_roles(...)` 权限依赖；
- 在认证模式下从 token 注入 `tenant_id`；
- 保留 `AUTH_ENABLED=false` 兼容模式，避免破坏旧测试和旧演示；
- 完成 `.env` / API Key / JWT secret 配置治理。

本窗口不做：

- 不做 SSO / OAuth2 / 第三方登录；
- 不做复杂组织架构；
- 不做菜单权限；
- 不做字段级权限；
- 不重构 RAG 主链路；
- 不重构客服 Agent / 导购 Agent / 运营 Copilot；
- 不重构内容生成审核流；
- 不重构评测中心；
- 不让默认 pytest 依赖真实模型或登录流程。

---

## 2. 新增 / 修改文件清单

### 2.1 新增文件

认证与安全：

- `backend/app/core/security.py`
- `backend/app/core/auth_dependencies.py`
- `backend/app/api/v1/auth.py`
- `backend/app/schemas/auth.py`
- `backend/app/services/auth_service.py`
- `backend/app/models/auth.py`

数据库迁移：

- `backend/alembic/versions/e13_create_auth_account.py`

脚本：

- `backend/scripts/seed_auth_accounts.py`

测试：

- `backend/tests/test_auth_service.py`
- `backend/tests/test_auth_api.py`
- `backend/tests/test_rbac_dependencies.py`
- `backend/tests/test_rbac_api.py`

文档与配置治理：

- `.gitignore`
- `docs/window13_handoff.md`

### 2.2 修改文件

配置：

- `backend/app/core/config.py`
- `backend/.env.example`
- `docker-compose.yml`

路由注册与模型注册：

- `backend/app/api/v1/router.py`
- `backend/app/models/__init__.py`

RBAC 接入：

- `backend/app/api/v1/prompts.py`
- `backend/app/api/v1/knowledge.py`
- `backend/app/api/v1/content.py`
- `backend/app/api/v1/evaluations.py`

文档：

- `README.md`
- `docs/deployment_guide.md`
- `docs/demo_script.md`
- `docs/resume_highlights.md`

配置治理：

- `backend/.env` 从 Git 跟踪中移除；
- `backend/.venv/` 从 Git 跟踪中移除；
- `__pycache__` / `*.pyc` 从 Git 跟踪中移除。

说明：工作区中仍存在部分窗口 8 / 9 / 10 / 11 / 12 的上游成果文件，例如导购 Agent 增强、运营
Copilot、内容生成审核流、评测中心、部署文档等。这些不是窗口 13 新增范围，但属于当前 v1.0 至 v1.1 集成基线的一部分，不应删除。

---

## 3. 数据库变更

### 3.1 新增表：`auth_account`

新增 Alembic migration：

```text
backend/alembic/versions/e13_create_auth_account.py
```

当前数据库版本：

```text
e13_create_auth_account (head)
```

### 3.2 字段设计

`auth_account` 字段：

- `id`
- `tenant_id`
- `user_id`
- `username`
- `password_hash`
- `role`
- `status`
- `last_login_at`
- `created_at`
- `updated_at`
- `deleted_at`

### 3.3 约束与索引

角色约束：

```text
admin
operator
viewer
```

状态约束：

```text
active
disabled
```

唯一约束：

```text
tenant_id + username
```

索引：

- `tenant_id`
- `deleted_at`
- `tenant_id + user_id`
- `tenant_id + role`
- `tenant_id + status`

### 3.4 设计取舍

本窗口没有把登录账号字段塞进 `user_profile`，而是新增 `auth_account`。

原因：

- `user_profile` 是业务用户画像表；
- 登录账号需要 `username / password_hash / role / status / last_login_at` 等安全字段；
- 两者职责不同，强行混用会污染业务模型；
- `auth_account.user_id` 关联 `user_profile.id`，既能复用现有业务用户，又保持认证模型独立。

---

## 4. Auth / RBAC 设计说明

### 4.1 认证接口

新增接口：

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

登录请求：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

登录成功返回：

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "account_id": "...",
    "user_id": "...",
    "user_no": "U100001",
    "username": "admin",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "role": "admin"
  }
}
```

### 4.2 密码存储

密码不明文存储。

实现：

- 使用标准库 `hashlib.pbkdf2_hmac`;
- 算法：PBKDF2-HMAC-SHA256；
- salt 使用 `secrets.token_hex`;
- hash 格式：

```text
pbkdf2_sha256$iterations$salt$hash
```

### 4.3 JWT 实现

本窗口未引入 `PyJWT`、`python-jose`、`passlib` 等外部依赖。

原因：

- 当前项目依赖体系已经稳定；
- 窗口 13 是轻量生产化增强；
- 避免新增依赖导致 Docker build 和测试环境不稳定；
- HS256 JWT 和 PBKDF2 密码 hash 可以由标准库满足本窗口需求。

JWT 使用标准库实现：

- `hmac`
- `hashlib`
- `base64`
- `json`
- `time`

支持：

- HS256 签发；
- 签名校验；
- `exp` 过期校验；
- token 格式校验；
- algorithm 校验。

---

## 5. JWT Claims 设计

JWT claims 至少包含：

```json
{
  "sub": "user_id",
  "account_id": "auth_account.id",
  "user_id": "user_profile.id",
  "user_no": "U100001",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "role": "admin",
  "exp": 1234567890
}
```

说明：

- `sub` 使用 `user_id`；
- `account_id` 用于回查 `auth_account`；
- `user_id` 对应 `user_profile.id`；
- `user_no` 用于业务侧展示和演示；
- `tenant_id` 用于租户隔离；
- `role` 用于 RBAC；
- `exp` 用于 token 过期校验。

---

## 6. 角色权限说明

当前角色：

| role     | 权限定位                               |
|----------|------------------------------------|
| admin    | 管理员，可执行 Prompt、知识库、内容审批、评测执行等高权限操作 |
| operator | 运营人员，可使用业务 Agent、内容生成、提交内容审核       |
| viewer   | 只读用户，不允许执行写操作、高权限审批或评测执行           |

本窗口已实现 `require_roles(...)` 依赖。

示例：

```python
current_user: CurrentUser | None = Depends(require_roles("admin"))
```

在 `AUTH_ENABLED=false` 时：

- `require_roles(...)` no-op；
- 返回 `None` 或已解析用户；
- 旧接口不因缺少 token 被阻断。

在 `AUTH_ENABLED=true` 时：

- 无 token 返回 401；
- 角色不足返回 403；
- token 无效或过期返回 401。

---

## 7. tenant_id 注入策略

### 7.1 兼容模式

当：

```env
AUTH_ENABLED=false
```

行为：

- 保持旧 API 合同；
- 请求仍可显式传入 `tenant_id`；
- 不强制要求 Bearer Token；
- 默认 pytest 和旧演示不受影响。

### 7.2 认证模式

当：

```env
AUTH_ENABLED=true
```

行为：

- 从 JWT claims 解析 `tenant_id`；
- 将当前用户写入 `request.state.user_id`；
- 将当前租户写入 `request.state.tenant_id`；
- 业务接口优先使用 token 中的 `tenant_id`；
- 如果请求中也传入 `tenant_id`，必须与 token 中 `tenant_id` 一致；
- 不一致返回 403。

核心函数：

```python
ensure_tenant_allowed(...)
```

返回策略：

- `AUTH_ENABLED=false`：返回请求中的 `tenant_id`；
- `AUTH_ENABLED=true`：返回 token 中的 `tenant_id`；
- 如果请求 `tenant_id` 与 token `tenant_id` 不一致：抛出 `ForbiddenException("Tenant mismatch")`。

---

## 8. AUTH_ENABLED / dev-test 兼容策略

新增配置：

```env
AUTH_ENABLED=false
JWT_SECRET_KEY=change_me_in_local_env
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

默认：

```env
AUTH_ENABLED=false
```

原因：

- v1.0 大量接口仍显式传入 `tenant_id`；
- 全量测试和演示脚本已经稳定；
- 窗口 13 不应为了认证改造大面积破坏原 API 合同；
- 兼容模式保证旧测试、旧演示继续通过。

生产化演示：

```powershell
$env:AUTH_ENABLED="true"
docker compose up -d --build backend
```

验证容器配置：

```powershell
docker compose exec backend python -c "from app.core.config import get_settings; s=get_settings(); print('AUTH_ENABLED=', s.auth_enabled)"
```

---

## 9. 配置治理说明

### 9.1 `.gitignore`

新增 `.gitignore`，覆盖：

- `.env`
- `.env.*`
- `backend/.env`
- `backend/.env.*`
- 保留 `.env.example`
- 保留 `backend/.env.example`
- `backend/.venv/`
- `__pycache__/`
- `*.pyc`
- 测试缓存、构建产物、日志和临时文件

### 9.2 `.env` 治理

当前状态：

```text
git ls-files .env backend/.env .env.example backend/.env.example
backend/.env.example
```

说明：

- `backend/.env` 本地仍存在；
- `backend/.env` 已从 Git 跟踪中移除；
- Git 只跟踪 `backend/.env.example`。

### 9.3 API Key / JWT secret 安全

规则：

- 不允许把真实 API Key 写进代码；
- 不允许把真实 API Key 写进 README；
- 不允许把真实 API Key 写进测试文件；
- 不允许把真实 API Key 写进交接文档；
- 不允许把真实 JWT secret 写进代码、README、测试文件或交接文档；
- 真实密钥只能通过本地 `.env` 或临时环境变量注入；
- 默认测试继续使用 mock provider；
- 真实模型只用于 smoke test。

### 9.4 Docker Compose 配置

`docker-compose.yml` 已支持：

```yaml
AUTH_ENABLED: ${AUTH_ENABLED:-false}
JWT_SECRET_KEY: ${JWT_SECRET_KEY:-change_me_in_local_env}
JWT_ALGORITHM: ${JWT_ALGORITHM:-HS256}
JWT_EXPIRE_MINUTES: ${JWT_EXPIRE_MINUTES:-1440}
```

---

## 10. 已接入 RBAC 的关键接口

### 10.1 Prompt 管理写接口

已接入 `admin`：

- 创建 Prompt Template；
- 更新 Prompt Template；
- 停用 Prompt Template；
- 归档 Prompt Template；
- 创建 Prompt Version；
- 激活 Prompt Version；
- 停用 Prompt Version。

### 10.2 Knowledge

已接入 `admin`：

- Knowledge 文档上传。

说明：

- 当前知识库路由没有删除接口；
- 本窗口只保护上传类高风险写入口；
- 查询、搜索、问答保持兼容。

### 10.3 Content

已接入：

- 提交审核：`admin / operator`
- 审批通过：`admin`
- 驳回：`admin`

认证模式下：

- `operator_id` / `reviewer_id` 优先使用当前 token 用户；
- 不完全信任前端显式传入的操作者字段。

### 10.4 Evaluations

已接入 `admin`：

- RAG evaluation run；
- Agent evaluation run。

---

## 11. 暂未强制接入认证的接口

暂未强制保护：

- 客服 Agent 对话接口；
- 导购 Agent 对话接口；
- 运营 Copilot 对话 / 查询接口；
- 大部分只读查询接口；
- RAG search / ask 查询类接口。

原因：

- 这些是 v1.0 已通过的主演示链路；
- 窗口 13 要求不大面积重写 API；
- 默认测试和演示必须继续稳定；
- 当前重点是补齐关键写操作和高权限操作的生产化边界；
- 后续可基于前端登录态逐步扩展到所有接口。

---

## 12. 测试命令与结果

### 12.1 Auth / RBAC 专项测试

命令：

```powershell
cd D:\omni-commerce-ai\backend

$env:TEST_API_BASE_URL="http://127.0.0.1:8002"
$env:API_BASE_URL="http://127.0.0.1:8002"
$env:AUTH_ENABLED="false"

python -m pytest tests/test_auth_service.py tests/test_auth_api.py tests/test_rbac_dependencies.py -q
```

结果：

```text
13 passed in 2.81s
```

### 12.2 生产化认证模式 API 级 RBAC 测试

启动认证模式：

```powershell
cd D:\omni-commerce-ai

$env:AUTH_ENABLED="true"
docker compose up -d --build backend
```

确认：

```powershell
docker compose exec backend python -c "from app.core.config import get_settings; s=get_settings(); print('AUTH_ENABLED=', s.auth_enabled)"
```

输出：

```text
AUTH_ENABLED= True
```

执行：

```powershell
cd D:\omni-commerce-ai\backend

$env:AUTH_ENABLED="true"
$env:API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/test_rbac_api.py -q
```

结果：

```text
4 passed in 1.45s
```

### 12.3 默认兼容模式全量回归

恢复兼容模式：

```powershell
cd D:\omni-commerce-ai

$env:AUTH_ENABLED="false"
docker compose up -d --build backend
```

确认：

```powershell
docker compose exec backend python -c "from app.core.config import get_settings; s=get_settings(); print('AUTH_ENABLED=', s.auth_enabled)"
```

输出：

```text
AUTH_ENABLED= False
```

执行：

```powershell
cd D:\omni-commerce-ai\backend

$env:AUTH_ENABLED="false"
$env:API_BASE_URL="http://127.0.0.1:8002"
$env:TEST_API_BASE_URL="http://127.0.0.1:8002"

python -m pytest tests/ -q
```

结果：

```text
130 passed, 4 skipped, 1 warning in 24.70s
```

说明：

- 4 skipped 为 `tests/test_rbac_api.py`；
- 该测试要求 backend 以 `AUTH_ENABLED=true` 运行；
- 默认兼容模式下跳过是预期行为。

---

## 13. 已知问题与边界

### 13.1 仍保留显式 tenant_id

当前大量旧接口仍保留显式 `tenant_id` 参数。

这不是 bug，而是过渡设计：

- `AUTH_ENABLED=false`：继续使用请求中的 `tenant_id`；
- `AUTH_ENABLED=true`：优先使用 token 中的 `tenant_id`；
- 如果请求中也传入 `tenant_id`，必须一致。

### 13.2 Agent 接口未强制认证

Agent 对话接口暂未强制接入认证。

原因：

- 保留 v1.0 演示稳定性；
- 避免为窗口 13 大面积重写 Agent 协议；
- 后续可以在前端登录态完善后逐步接入。

### 13.3 未做复杂 IAM

本窗口未做：

- SSO；
- OAuth2；
- 第三方登录；
- 组织架构；
- 菜单权限；
- 字段级权限；
- 审批流权限矩阵。

这是刻意控制范围，避免把轻量生产化增强做成复杂 IAM 工程。

### 13.4 Runtime warning

默认全量测试仍存在一个历史 warning：

```text
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
```

该 warning 在窗口 13 前已存在类似表现，不影响当前测试通过。窗口 13 未对底层 asyncpg 连接生命周期做大规模重构。

---

## 14. 验收结论

窗口 13 已完成。

完成情况：

- 轻量认证体系已完成；
- JWT 登录态已完成；
- 密码 hash 已完成；
- current_user / current_tenant 依赖已完成；
- admin / operator / viewer 三角色 RBAC 已完成；
- `require_roles(...)` 已完成；
- token tenant_id 注入与 tenant mismatch 拦截已完成；
- `AUTH_ENABLED=false / true` 双模式已完成；
- `.env` / API Key / JWT secret 配置治理已完成；
- 关键写接口已接入 RBAC；
- 默认兼容模式全量测试通过；
- 生产化认证模式 API 级 RBAC 测试通过。

最终验证：

```text
AUTH_ENABLED=false:
130 passed, 4 skipped, 1 warning

AUTH_ENABLED=true:
tests/test_rbac_api.py -> 4 passed
```