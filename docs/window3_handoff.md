# 模块交接文档：执行窗口 3 - 基础业务服务

> 最终合并版，含回炉补丁

## 一、文档状态

| 项目         | 内容          |
|------------|-------------|
| 当前窗口       | 执行窗口 3      |
| 模块名称       | 基础业务服务      |
| 当前状态       | 已完成         |
| 回炉补丁状态     | 已完成         |
| 是否建议进入下一窗口 | 是           |
| 建议进入       | 执行窗口 4：模型网关 |

本窗口最初完成了基础业务服务接口、service 层和 repository 层。

总控驳回后，已补齐窗口 3 专属 API 自动化测试，并修正 Docker build 稳定性问题。

此前 `TestClient` 导致的 `asyncpg` 跨事件循环错误已定位并修复，问题来源于旧测试文件仍使用：

```python
fastapi.testclient.TestClient
```

进程内调用 FastAPI 应用。

---

## 二、模块目标

执行窗口 3 负责实现电商业务基础服务，为后续客服 Agent、导购 Agent、运营 Copilot 等模块提供可复用的业务 service 层能力。

本窗口只实现基础业务查询与创建能力，不实现：

- Agent；
- RAG；
- 模型调用；
- Prompt 管理；
- 认证；
- 权限系统。

---

## 三、上游依赖

本窗口依赖：

- 执行窗口 1：基础工程骨架；
- 执行窗口 2：核心数据模型。

其中，窗口 2 已提供核心数据模型和种子数据，本窗口基于这些模型实现：

- 业务 API；
- schemas；
- repositories；
- services。

---

## 四、窗口边界

---

### 4.1 本窗口完成范围

已完成：

- 用户画像查询；
- 商品列表查询；
- 商品详情查询；
- SKU 列表查询；
- SKU 详情查询；
- 商品评价查询；
- 订单列表查询；
- 订单详情查询；
- 售后单列表查询；
- 售后单详情查询；
- 售后单创建；
- 客服工单列表查询；
- 客服工单详情查询；
- 客服工单创建；
- 后台商品列表查询；
- 后台商品详情查询；
- 统一响应格式；
- 统一业务异常；
- 参数校验异常统一响应；
- API / schemas / services / repositories 分层；
- 窗口 3 专属 API 自动化测试；
- Docker build 稳定性修正。

---

### 4.2 本窗口禁止范围

本窗口未做，也不应做：

- 不改 `tenant_id` 认证上下文；
- 不做 JWT / RBAC；
- 不引入统一业务单号生成器；
- 不改数据库表结构；
- 不做模型网关；
- 不做 Prompt；
- 不做 RAG；
- 不做 Agent；
- 不把业务逻辑写在 API 层；
- 不直接做 Agent 工具。

---

## 五、新增文件清单

---

### 5.1 API 层

```text
backend/app/api/v1/helpers.py
backend/app/api/v1/users.py
backend/app/api/v1/products.py
backend/app/api/v1/orders.py
backend/app/api/v1/aftersales.py
backend/app/api/v1/tickets.py
```

---

### 5.2 Schema 层

```text
backend/app/schemas/__init__.py
backend/app/schemas/common.py
backend/app/schemas/user.py
backend/app/schemas/product.py
backend/app/schemas/order.py
backend/app/schemas/aftersale.py
backend/app/schemas/ticket.py
```

---

### 5.3 Repository 层

```text
backend/app/repositories/__init__.py
backend/app/repositories/user_repository.py
backend/app/repositories/product_repository.py
backend/app/repositories/order_repository.py
backend/app/repositories/aftersale_repository.py
backend/app/repositories/ticket_repository.py
```

---

### 5.4 Service 层

```text
backend/app/services/__init__.py
backend/app/services/user_service.py
backend/app/services/product_service.py
backend/app/services/order_service.py
backend/app/services/aftersale_service.py
backend/app/services/ticket_service.py
```

---

### 5.5 自动化测试

回炉补丁新增：

```text
backend/tests/test_products_api.py
backend/tests/test_orders_api.py
backend/tests/test_aftersales_api.py
backend/tests/test_tickets_api.py
```

---

## 六、修改文件清单

```text
backend/app/api/v1/router.py
backend/Dockerfile
docker-compose.yml
```

---

### 6.1 `backend/app/api/v1/router.py`

已挂载：

```text
health_router
users_router
products_router
orders_router
aftersales_router
tickets_router
```

---

### 6.2 `backend/Dockerfile`

已加入：

```dockerfile
ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_DEFAULT_TIMEOUT=100
```

说明：

- 默认使用官方 PyPI；
- 允许构建时通过 `build-arg` 切换 pip 镜像源；
- 未把国内镜像源写死为唯一方案；
- 同时移除了非必要的 `apt-get install build-essential curl`，降低 Debian apt 源断流导致 build 失败的概率。

---

### 6.3 `docker-compose.yml`

`backend build` 已支持传递 pip 源参数：

```yaml
backend:
  build:
    context: ./backend
    args:
      PIP_INDEX_URL: ${PIP_INDEX_URL:-https://pypi.org/simple}
```

---

## 七、数据库变更

---

### 7.1 新增数据表

无。

---

### 7.2 修改数据表

无。

---

### 7.3 Alembic 迁移

本窗口未新增 Alembic 迁移。

当前依赖窗口 2 迁移版本：

```text
9c9c22e1cf47_create_core_data_models.py
```

当前数据库版本已验证：

```text
9c9c22e1cf47 (head)
```

---

### 7.4 测试数据说明

窗口 3 接口测试依赖窗口 2 种子数据，例如：

```text
tenant_id = 00000000-0000-0000-0000-000000000001
user_no = U100001
product_no = P100001
sku_no = SKU100001
order_no = O100001
after_sale_ticket_no = AS100001
customer_service_ticket_no = CS100001
```

售后单创建测试和客服工单创建测试会写入新测试数据。

断言未依赖固定 `total`，因此重复运行不会影响测试通过。

---

## 八、API 接口清单

---

### 8.1 用户接口

```http
GET /api/v1/users/{user_no}
```

说明：

> 查询用户画像。

---

### 8.2 商品接口

```http
GET /api/v1/products
GET /api/v1/products/{product_no}
GET /api/v1/products/{product_no}/skus
GET /api/v1/products/skus/{sku_no}
GET /api/v1/products/{product_no}/reviews
```

说明：

- 用户侧商品接口默认只返回 `active` 商品；
- SKU 查询默认只返回 `active` SKU；
- 评价查询默认只返回 `visible` 评价。

---

### 8.3 后台商品接口

```http
GET /api/v1/products/admin/list
GET /api/v1/products/admin/{product_no}
```

说明：

- 后台商品列表可查看 `active` / `inactive` 等未软删除商品；
- 可通过 `status` 参数筛选商品状态；
- 当前未接 RBAC，后续认证窗口完成后应补权限控制。

---

### 8.4 订单接口

```http
GET /api/v1/orders
GET /api/v1/orders/{order_no}
```

说明：

- 支持按用户编号筛选；
- 支持按订单状态筛选；
- 支持按支付状态筛选；
- 支持按履约状态筛选；
- 订单详情返回订单主信息、订单明细、收货快照、支付快照、物流快照。

---

### 8.5 售后接口

```http
GET  /api/v1/aftersales
POST /api/v1/aftersales
GET  /api/v1/aftersales/{ticket_no}
```

说明：

- 支持售后单列表查询；
- 支持售后单详情查询；
- 支持基础售后单创建；
- 创建时校验用户存在、订单存在、订单归属用户、订单明细归属订单。

---

### 8.6 客服工单接口

```http
GET  /api/v1/tickets
POST /api/v1/tickets
GET  /api/v1/tickets/{ticket_no}
```

说明：

- 支持客服工单列表查询；
- 支持客服工单详情查询；
- 支持基础客服工单创建；
- 当前不做 Agent 转人工策略，只提供可复用 service 能力。

---

## 九、自动化测试覆盖范围

---

### 9.1 商品 API 测试

文件：

```text
backend/tests/test_products_api.py
```

覆盖接口：

```http
GET /api/v1/products
GET /api/v1/products/{product_no}
GET /api/v1/products/{product_no}/skus
GET /api/v1/products/skus/{sku_no}
GET /api/v1/products/{product_no}/reviews
```

覆盖路径：

- 商品列表成功路径；
- 商品详情成功路径；
- SKU 列表成功路径；
- SKU 详情成功路径；
- 商品评价成功路径；
- 商品不存在；
- SKU 不存在；
- `tenant_id` 非法。

---

### 9.2 订单 API 测试

文件：

```text
backend/tests/test_orders_api.py
```

覆盖接口：

```http
GET /api/v1/orders
GET /api/v1/orders/{order_no}
```

覆盖路径：

- 订单列表成功路径；
- 按用户查询订单成功路径；
- 订单详情成功路径；
- 订单不存在；
- 用户不存在；
- `tenant_id` 非法。

---

### 9.3 售后 API 测试

文件：

```text
backend/tests/test_aftersales_api.py
```

覆盖接口：

```http
GET  /api/v1/aftersales
POST /api/v1/aftersales
GET  /api/v1/aftersales/{ticket_no}
```

覆盖路径：

- 售后单列表成功路径；
- 售后单详情成功路径；
- 售后单创建成功路径；
- 售后单不存在；
- 创建售后单时订单不存在；
- `tenant_id` 非法。

---

### 9.4 客服工单 API 测试

文件：

```text
backend/tests/test_tickets_api.py
```

覆盖接口：

```http
GET  /api/v1/tickets
POST /api/v1/tickets
GET  /api/v1/tickets/{ticket_no}
```

覆盖路径：

- 客服工单列表成功路径；
- 客服工单详情成功路径；
- 客服工单创建成功路径；
- 客服工单不存在；
- 创建客服工单时订单不存在；
- `tenant_id` 非法。

---

## 十、测试实现方式说明

窗口 3 API 测试最终采用 `httpx` 调用运行中的 backend 服务：

```python
BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
```

原因：

- 初版测试使用 `FastAPI TestClient(app)` 进程内调用应用；
- 项目当前使用 SQLAlchemy Async + `asyncpg` 连接池；
- 多用例运行时出现 `asyncpg` 连接绑定不同 event loop 的问题；
- 典型错误为 `Future attached to a different loop`。

最终处理方式：

- 不改业务代码；
- 不改数据库连接实现；
- 将窗口 3 API 自动化测试改为 `httpx` 调用运行中的 backend 服务；
- 测试目标更贴近真实 API 调用链路。

最终已确认容器内窗口 3 测试文件不再包含：

```text
TestClient
client = TestClient
from app.main import app
```

---

## 十一、测试结果

---

### 11.1 窗口 3 专属 API 测试

运行命令：

```powershell
docker compose exec backend python -m pytest `
  tests/test_products_api.py `
  tests/test_orders_api.py `
  tests/test_aftersales_api.py `
  tests/test_tickets_api.py
```

实际结果：

```text
collected 26 items

tests/test_products_api.py ........
tests/test_orders_api.py ......
tests/test_aftersales_api.py ......
tests/test_tickets_api.py ......

26 passed in 2.92s
```

---

### 11.2 全量测试

运行命令：

```bash
docker compose exec backend python -m pytest tests/
```

实际结果：

```text
collected 33 items

tests/test_aftersales_api.py ......
tests/test_exceptions.py ..
tests/test_health.py .
tests/test_middleware.py ..
tests/test_orders_api.py ......
tests/test_products_api.py ........
tests/test_response.py ..
tests/test_tickets_api.py ......

33 passed in 3.02s
```

---

## 十二、Docker build 验证方式

---

### 12.1 默认官方 PyPI

```bash
docker compose build backend --no-cache
```

---

### 12.2 指定 pip 镜像源

清华源：

```powershell
$env:PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
docker compose build backend --no-cache
```

阿里源：

```powershell
$env:PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
docker compose build backend --no-cache
```

---

### 12.3 启动服务

```bash
docker compose up -d backend
```

---

### 12.4 验证服务

```bash
docker compose exec backend python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/health').json())"
```

预期：

```text
success = True
code = OK
database = ok
redis = ok
```

---

### 12.5 验证迁移版本

```bash
docker compose exec backend python -m alembic current
```

预期：

```text
9c9c22e1cf47 (head)
```

---

## 十三、运行方式

---

### 13.1 启动全部服务

```bash
docker compose up -d
```

---

### 13.2 查看服务状态

```bash
docker compose ps
```

---

### 13.3 健康检查

容器内：

```bash
docker compose exec backend python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/health').json())"
```

宿主机：

```bash
curl.exe "http://127.0.0.1:8002/api/v1/health"
```

---

### 13.4 设置测试租户变量

```powershell
$TENANT_ID="00000000-0000-0000-0000-000000000001"
```

---

## 十四、核心实现决策

---

### 决策 1：`tenant_id` 暂时显式传参

当前接口通过 query 或 body 显式传入 `tenant_id`。

原因：

- 认证 / RBAC 尚未实现；
- 当前无法从登录上下文读取租户。

后续：

- 认证完成后，从 JWT / request context 获取 `tenant_id`；
- 接口可逐步移除显式 `tenant_id`。

---

### 决策 2：普通商品接口只返回 `active` 商品

用户侧商品列表、详情、SKU 查询默认过滤：

```text
status = active
```

原因：

> 避免下架商品出现在用户侧。

后续：

> 如需预览下架商品，应走后台接口。

---

### 决策 3：后台商品接口可查询 `inactive` 商品

`/products/admin/list` 支持不传 `status`，返回所有未软删除商品。

原因：

> 基础后台管理需要看到下架商品。

后续：

> 接入 RBAC 后限制为 admin / operator 角色。

---

### 决策 4：评价默认只返回 `visible`

商品评价查询默认过滤：

```text
status = visible
```

原因：

> 隐藏、待审核评价不应暴露给用户侧。

后续：

> 后台评价管理可新增独立接口。

---

### 决策 5：repository 不提交事务

repository 的 `create` 方法只执行：

```text
flush / refresh
```

不执行：

```text
commit
```

原因：

- 事务边界应由 service 层控制；
- 方便组合多个 repository 操作。

建议：

> 保持当前方式，不建议改为 repository 内提交。

---

### 决策 6：售后单号 / 工单号局部生成

当前使用：

```text
前缀 + UTC 时间戳 + UUID 短码
```

生成业务单号。

原因：

- 窗口 3 不引入全局发号器；
- 避免越权新增公共能力。

后续：

> 如需要严格递增或分布式发号，应由总控确认统一编号服务。

---

### 决策 7：创建客服工单允许 `source=agent`

`CustomerServiceTicketCreateRequest.source` 支持：

```text
manual
agent
api
```

原因：

> 窗口 7 客服 Agent 后续可能复用该 service 创建工单。

后续：

> 接入 Agent 后由 tools 层调用 service，不直接查库。

---

## 十五、已知问题

当前仍存在但不阻塞窗口 4 的问题：

1. API 测试依赖窗口 2 种子数据，不是完全隔离测试；
2. 售后单创建和客服工单创建测试会写入测试数据，重复运行会增加记录数；
3. 当前认证 / RBAC 未实现，`tenant_id` 需要显式传入；
4. 当前后台接口未做权限控制，后续认证模块完成后必须补 RBAC；
5. 当前 PowerShell 控制台显示长 JSON 或中文时偶尔出现乱码 / 断裂，但接口结构和入库结果正常；
6. Docker build 稳定性已改善，但仍取决于当前网络环境；已支持通过 `build-arg` 切换 pip 源。

---

## 十六、已修复问题

---

### 16.1 Docker build 依赖下载不稳定

原问题：

- Docker build 过程中访问 PyPI 或 Debian apt 源不稳定；
- 曾出现 pip 下载超时、依赖索引拉取失败、apt 下载 gcc 包断流。

修复：

- Dockerfile 增加 `ARG PIP_INDEX_URL`；
- 支持构建时切换 pip 源；
- 移除非必要 `apt-get build-essential / curl` 安装步骤；
- 不再依赖 `docker compose cp` 作为最终验证方式。

---

### 16.2 API 自动化测试缺失

原问题：

> 窗口 3 缺少专属 API 自动化测试。

修复：

- 新增 `test_products_api.py`；
- 新增 `test_orders_api.py`；
- 新增 `test_aftersales_api.py`；
- 新增 `test_tickets_api.py`；
- 共覆盖 26 条窗口 3 API 测试。

---

### 16.3 `TestClient` 与 `asyncpg` 事件循环冲突

原问题：

- 初版 API 测试使用 `TestClient(app)`；
- 多用例运行时触发 `asyncpg` 跨 event loop 错误。

修复：

- 改为 `httpx` 调用运行中的 backend 服务；
- 窗口 3 专属测试 `26 passed`；
- 全量测试 `33 passed`。

---

## 十七、给执行窗口 4 的注意事项

执行窗口 4 是模型网关，应注意：

1. 不要绕过当前 service / repository 分层；
2. 模型网关只做模型调用统一入口，不要顺手改业务接口；
3. 窗口 4 不需要调用商品、订单、售后接口，除非做最小测试接口；
4. 后续 Agent 工具应复用本窗口 service 层能力，而不是直接查数据库；
5. `ticket_service.py` 和 `aftersale_service.py` 可被窗口 7 工具层复用；
6. 商品服务已区分用户侧和后台侧接口，Agent 推荐商品时应优先使用用户侧 `active` 商品逻辑；
7. 评价接口只返回 `visible` 评价，导购 Agent 后续做评价摘要时应复用该策略；
8. 后续如果继续新增 API 测试，注意不要重新引入 `TestClient(app)` 触发 `asyncpg event loop` 问题；
9. Docker build 已支持 `PIP_INDEX_URL` 参数，遇到网络不稳定时可切换 pip 源。

---

## 十八、需总控确认事项

---

### 事项 1：后续是否引入统一业务单号生成器

当前售后单和客服工单使用局部单号生成逻辑：

```text
prefix + timestamp + uuid suffix
```

建议：

> 如后续订单、工单、Agent 任务都需要统一编号，应由总控确认统一编号服务。

是否阻塞窗口 4：

```text
不阻塞
```

---

### 事项 2：后续是否将 `tenant_id` 改为认证上下文读取

当前接口显式传入 `tenant_id`。

建议：

> 认证模块完成后，从 JWT 或 request context 注入 `tenant_id`。

是否阻塞窗口 4：

```text
不阻塞
```

---

### 事项 3：后续是否增加测试隔离机制

当前 API 测试依赖窗口 2 种子数据，创建类测试会写入记录。

建议：

> 后续可引入专用测试数据库、事务回滚 fixture 或测试数据清理脚本。

是否阻塞窗口 4：

```text
不阻塞
```

---

## 十九、本窗口交付结论

| 项目         | 结果          |
|------------|-------------|
| 自评状态       | 已完成         |
| 回炉补丁       | 已完成         |
| 是否建议进入下一窗口 | 是           |
| 建议进入       | 执行窗口 4：模型网关 |

原因说明：

- 基础业务服务接口已完成；
- API / schemas / services / repositories 分层清楚；
- 未越界实现 Agent / RAG / 模型调用；
- 回炉补齐窗口 3 专属 API 自动化测试；
- Docker build 稳定性问题已改善；
- `TestClient + asyncpg` 跨事件循环问题已修复；
- 窗口 3 专属 API 测试 `26 passed`；
- 全量测试 `33 passed`。

---

## 二十、一句话交接总结

执行窗口 3 已完成智营 OmniCommerce AI 的基础业务服务层建设，并在回炉补丁中补齐了 API 自动化测试和 Docker build 稳定性修正。

当前已覆盖：

```text
用户
商品
SKU
评价
订单
售后
客服工单
后台商品查询
```

后续执行窗口 4 可以在此基础上进入模型网关建设，但必须坚持：

```text
模型网关只负责统一模型调用入口
不要顺手改业务接口
后续 Agent 工具应复用 service 层
不要直接查数据库
```