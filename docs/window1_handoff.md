# 模块交接文档：执行窗口 1 - 基础工程骨架

## 1. 模块目标

本模块负责搭建 FastAPI 企业级后端基础工程骨架，为后续核心数据模型、基础业务服务、模型网关、Prompt 管理、RAG、Agent、评测中心和可观测性模块提供统一的项目结构、配置系统、响应格式、异常处理、结构化日志、请求追踪、数据库连接、Redis 连接和 Docker Compose 基础环境。

## 2. 窗口识别结果

- 当前执行窗口：执行窗口 1
- 当前窗口名称：基础工程骨架
- 本窗口目标：搭建正式工程级 FastAPI 后端基础工程骨架。
- 本窗口必须完成：FastAPI 项目结构、pyproject.toml、配置系统、统一响应格式、统一异常处理、结构化日志、request_id 中间件、PostgreSQL 连接、Redis 连接、Alembic 初始化、Dockerfile、docker-compose.yml 基础服务、健康检查接口、基础 README。
- 本窗口禁止完成：商品业务、订单业务、售后业务、工单业务、Agent、RAG、Prompt 管理、模型网关真实调用、评测中心、前端后台。
- 上游依赖：无。本窗口是执行窗口 1，没有上游交接文档。
- 最终交付物：可运行 FastAPI 后端骨架、Docker Compose 基础环境、Alembic 初始化、健康检查接口、基础测试、README、模块交接文档。
- 验收标准：项目可启动；/api/v1/health 可访问；统一响应格式生效；异常处理生效；request_id 生效；PostgreSQL 可连接；Redis 可连接；Alembic 可运行；Docker Compose 可拉起基础服务；不包含 Java / Spring 技术栈；不越权开发后续业务模块。

## 3. 已完成内容

- 已完成 FastAPI 项目基础目录结构。
- 已完成 pyproject.toml 依赖管理。
- 已完成基于 pydantic-settings 的配置系统。
- 已完成统一 API 响应结构。
- 已完成统一异常体系和全局异常处理。
- 已完成结构化 JSON 日志。
- 已完成 request_id 中间件，并写入响应体和 X-Request-ID 响应头。
- 已完成 PostgreSQL 异步连接配置。
- 已完成 Redis 异步连接配置。
- 已完成 Alembic 初始化。
- 已完成 Dockerfile。
- 已完成 docker-compose.yml，基础启用 backend、postgres、redis。
- 已完成 /api/v1/health 健康检查接口。
- 已完成基础 README。
- 已完成基础测试。

## 4. 新增文件清单

- README.md
- docker-compose.yml
- backend/Dockerfile
- backend/.dockerignore
- backend/.env.example
- backend/pyproject.toml
- backend/alembic.ini
- backend/alembic/env.py
- backend/alembic/script.py.mako
- backend/alembic/versions/
- backend/app/main.py
- backend/app/core/config.py
- backend/app/core/response.py
- backend/app/core/exceptions.py
- backend/app/core/logging.py
- backend/app/core/middleware.py
- backend/app/core/security.py
- backend/app/db/base.py
- backend/app/db/session.py
- backend/app/api/v1/router.py
- backend/app/api/v1/health.py
- backend/tests/test_response.py
- backend/tests/test_middleware.py
- backend/tests/test_exceptions.py
- backend/tests/test_health.py
- docs/window1_handoff.md

## 5. 修改文件清单

无。当前窗口为项目初始化窗口。

## 6. 数据库变更

### 6.1 新增数据表

无。

### 6.2 修改数据表

无。

### 6.3 Alembic 迁移

本窗口已初始化 Alembic，但未新增业务迁移文件。

当前没有业务表，因此不创建 migration revision。

### 6.4 字段说明

本窗口不涉及业务表字段。

## 7. API 接口清单

### 接口 1：根路径服务信息

- 方法：GET
- 路径：/
- 说明：用于快速确认服务启动状态。
- 请求参数：无。
- 响应字段：success、code、message、data、request_id。
- 响应 data 示例：app=omni-commerce-ai，env=dev，status=running。

### 接口 2：系统健康检查

- 方法：GET
- 路径：/api/v1/health
- 说明：用于系统健康检查，验证后端服务、PostgreSQL 连接、Redis 连接状态。
- 请求参数：无。
- 响应字段：success、code、message、data、request_id。
- 响应 data 示例：status=ok，database=ok，redis=ok，app=omni-commerce-ai，env=dev。

## 8. 配置项说明

| 配置项 | 说明 | 是否必填 | 默认值 |
| --- | --- | --- | --- |
| APP_NAME | 应用名称 | 否 | omni-commerce-ai |
| APP_ENV | 运行环境 | 否 | dev |
| APP_DEBUG | 是否开启调试配置 | 否 | true |
| DATABASE_URL | PostgreSQL 异步连接地址 | 是 | postgresql+asyncpg://omni:omni_password@localhost:5432/omni_ai |
| REDIS_URL | Redis 连接地址 | 是 | redis://localhost:6379/0 |
| JWT_SECRET_KEY | JWT 密钥预留 | 是 | change_me |
| JWT_ALGORITHM | JWT 算法预留 | 否 | HS256 |
| JWT_EXPIRE_MINUTES | JWT 过期分钟数预留 | 否 | 1440 |
| LOG_LEVEL | 日志级别 | 否 | INFO |

## 9. 运行方式

### Docker Compose 启动

在项目根目录执行：

- docker compose up -d --build

查看服务状态：

- docker compose ps

健康检查：

- curl http://127.0.0.1:8002/api/v1/health

进入后端容器：

- docker compose exec backend bash

Alembic 验证：

- docker compose exec backend python -m alembic current
- docker compose exec backend python -m alembic history

### 本地启动

在 backend 目录执行：

- python -m venv .venv
- .\.venv\Scripts\Activate.ps1
- python -m pip install -e ".[dev]"
- python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

## 10. 测试方式

### 单元测试

在 backend 目录执行：

- python -m pytest tests/

当前测试结果：

- 7 passed

### 健康检查测试

在项目根目录执行：

- curl http://127.0.0.1:8002/api/v1/health

预期核心结果：

- success=true
- code=OK
- data.status=ok
- data.database=ok
- data.redis=ok
- request_id=req_xxx

### 数据库迁移能力测试

在项目根目录执行：

- docker compose exec backend python -m alembic current
- docker compose exec backend python -m alembic history

当前窗口无迁移版本，因此 current 不输出具体版本号是正常情况；不报错即说明 Alembic 可连接 PostgreSQL 并能加载配置。

## 11. 局部实现决策

### 决策 1：统一使用 app.xxx 绝对导包

- 决策内容：项目内部导包统一使用 from app.xxx import xxx。
- 决策原因：保证本地启动、pytest、Docker、Alembic 使用同一套导包规则。
- 影响范围：影响所有后端 Python 模块。
- 后续可调整方式：不建议调整，除非整体改变后端包结构。

### 决策 2：FastAPI debug 固定为 False

- 决策内容：FastAPI 初始化时 debug=False，但保留 settings.app_debug 给其他开发配置使用。
- 决策原因：避免未处理异常返回调试 traceback，破坏统一异常响应格式。
- 影响范围：影响异常响应安全性和一致性。
- 后续可调整方式：如需调试，可通过日志和测试定位，不建议对前端暴露 traceback。

### 决策 3：健康检查依赖失败时返回 degraded

- 决策内容：PostgreSQL 或 Redis 任一失败时，接口仍返回统一成功响应，但 data.status 为 degraded。
- 决策原因：健康检查需要区分后端服务存活和外部依赖异常。
- 影响范围：影响监控和部署探活逻辑。
- 后续可调整方式：窗口 12 接入 Prometheus 后，可进一步拆分 readiness/liveness。

### 决策 4：宿主机 backend 端口使用 8002

- 决策内容：Docker Compose 中 backend 使用 8002:8000。
- 决策原因：本机已有 price-audit-api 容器占用 8000。
- 影响范围：本地访问地址为 http://127.0.0.1:8002。
- 后续可调整方式：如果释放宿主机 8000，可改回 8000:8000。

### 决策 5：窗口 1 只初始化 Alembic，不创建迁移版本

- 决策内容：Alembic 已初始化，但 versions 下无业务迁移。
- 决策原因：执行窗口 1 不负责核心数据模型，业务表应由执行窗口 2 创建。
- 影响范围：执行窗口 2 可直接基于当前 Alembic 配置生成迁移。
- 后续可调整方式：窗口 2 新增模型后执行 alembic revision --autogenerate。

## 12. 已知问题

1. 当前 Redis 仅完成基础连接检查，尚未封装缓存工具类。
2. 当前仅初始化 Alembic，未创建业务表迁移。
3. 当前 core/security.py 仅作为结构预留，未实现 JWT 登录和 RBAC。
4. 当前 Docker Compose 未接入 Qdrant、MinIO、OpenSearch、Prometheus、Grafana，只在注释中预留。
5. 当前宿主机 8000 被旧项目 price-audit-api 占用，因此本项目使用 8002 作为宿主机访问端口。

## 13. 需总控确认事项

暂无需总控确认事项。

## 14. 给下一个执行窗口的注意事项

1. 执行窗口 2 新增 SQLAlchemy 模型时，需要统一继承 backend/app/db/base.py 中的 Base。
2. 新增模型后，必须确保 Alembic 能检测到模型 metadata。
3. 核心业务表应按全局规范包含 tenant_id、created_at、updated_at、deleted_at。
4. 日志类表应按全局规范包含 request_id。
5. 不要修改统一响应字段：success、code、message、data、request_id。
6. 不要移除 RequestContextMiddleware。
7. 不要把业务逻辑写入 API 层。
8. 不要引入 Java / Spring 技术栈。
9. 如果释放本机 8000 端口，可将 docker-compose.yml 中 backend ports 改回 8000:8000。

## 15. 简历可沉淀亮点

- 搭建基于 FastAPI 的企业级后端工程骨架，封装统一响应、统一异常、配置管理和结构化日志体系。
- 基于 Docker Compose 编排 PostgreSQL、Redis 和 FastAPI 后端，实现基础环境一键启动。
- 设计 request_id 请求追踪机制，为后续模型调用链路、Agent 执行链路、工具调用日志和可观测性接入打基础。
- 使用 SQLAlchemy 2.0 Async 与 Alembic 构建可扩展的数据访问和迁移基础。
- 在项目第一阶段即建立可运行、可维护、可交接、可验收的工程规范，避免 Demo 化开发。

## 16. 本窗口交付结论

- 自评状态：已完成
- 是否建议进入下一窗口：是
- 原因说明：执行窗口 1 要求的 FastAPI 基础工程骨架、配置系统、统一响应、异常处理、结构化日志、request_id、PostgreSQL/Redis 连接、Alembic、Docker Compose、健康检查、README 和基础测试均已完成；未越权开发后续业务模块；未引入 Java / Spring 技术栈。
