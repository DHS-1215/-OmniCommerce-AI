# 智营 OmniCommerce AI

## 一、项目定位

智营 OmniCommerce AI 是一个面向电商业务场景的企业级大模型运营中台项目。

当前完成阶段：

```text
执行窗口 1：基础工程骨架
```

本阶段只负责搭建 FastAPI 后端基础工程骨架，不实现以下业务能力：

- 商品业务；
- 订单业务；
- Agent；
- RAG；
- Prompt 管理；
- 模型网关真实调用；
- 评测中心；
- 前端后台。

---

## 二、技术栈

- Python 3.11+
- FastAPI
- Pydantic v2
- pydantic-settings
- SQLAlchemy 2.0 Async
- Alembic
- PostgreSQL
- Redis
- Docker Compose

---

## 三、当前目录结构

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── response.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   ├── middleware.py
│   │   └── security.py
│   ├── db/
│   │   ├── session.py
│   │   └── base.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── health.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── agents/
│   ├── tools/
│   ├── rag/
│   ├── llm/
│   ├── prompts/
│   ├── evaluations/
│   ├── tasks/
│   ├── observability/
│   └── utils/
├── tests/
├── alembic/
├── Dockerfile
├── pyproject.toml
└── alembic.ini
```

---

## 四、环境变量

环境变量参考文件：

```text
backend/.env.example
```

核心配置示例：

```env
APP_NAME=omni-commerce-ai
APP_ENV=dev
APP_DEBUG=true

DATABASE_URL=postgresql+asyncpg://omni:omni_password@postgres:5432/omni_ai
REDIS_URL=redis://redis:6379/0

JWT_SECRET_KEY=change_me
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

LOG_LEVEL=INFO
```

---

## 五、Docker Compose 启动

当前本机 `8000` 端口被旧项目占用，因此本项目宿主机端口映射为：

```text
127.0.0.1:8002 -> backend 容器内 8000
```

### 5.1 启动服务

```bash
docker compose up -d --build
```

### 5.2 查看容器状态

```bash
docker compose ps
```

### 5.3 查看后端日志

```bash
docker compose logs backend --tail=100
```

---

## 六、健康检查

### 6.1 请求命令

```bash
curl http://127.0.0.1:8002/api/v1/health
```

### 6.2 预期返回

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "status": "ok",
    "database": "ok",
    "redis": "ok",
    "app": "omni-commerce-ai",
    "env": "dev"
  },
  "request_id": "req_xxx"
}
```

---

## 七、Alembic

当前窗口只初始化 Alembic，不创建业务表迁移。

### 7.1 查看当前迁移版本

```bash
docker compose exec backend python -m alembic current
```

### 7.2 查看迁移历史

```bash
docker compose exec backend python -m alembic history
```

后续执行窗口 2 新增数据模型后，再创建迁移文件。

---

## 八、本地开发

### 8.1 进入后端目录

```bash
cd backend
```

### 8.2 创建虚拟环境

```bash
python -m venv .venv
```

### 8.3 激活虚拟环境

```powershell
.\.venv\Scripts\Activate.ps1
```

### 8.4 安装依赖

```bash
python -m pip install -e ".[dev]"
```

### 8.5 本地启动

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### 8.6 本地测试

```bash
python -m pytest tests/
```

---

## 九、当前已完成能力

执行窗口 1 当前已完成：

- FastAPI 基础工程结构；
- 配置系统；
- 统一响应格式；
- 统一异常处理；
- `request_id` 中间件；
- 结构化 JSON 日志；
- PostgreSQL 异步连接；
- Redis 异步连接；
- Alembic 初始化；
- Dockerfile；
- Docker Compose 基础服务；
- 健康检查接口；
- 基础测试。

---

## 十、当前未实现内容

以下内容不属于执行窗口 1，后续窗口实现：

- 商品业务；
- 订单业务；
- 售后业务；
- 工单业务；
- Agent；
- RAG；
- Prompt 管理；
- 模型网关真实调用；
- 评测中心；
- 前端后台。

---

## 十一、当前阶段总结

执行窗口 1 已完成智营 OmniCommerce AI 的后端基础工程骨架搭建。

当前项目已经具备：

```text
可启动
可配置
可连接 PostgreSQL
可连接 Redis
可统一响应
可统一异常处理
可输出结构化日志
可通过 Docker Compose 运行
可进行健康检查
```

后续执行窗口 2 可以在此基础上继续推进数据库模型、业务实体与 Alembic 迁移文件建设。