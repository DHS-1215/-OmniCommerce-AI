# 简历亮点沉淀

本文档用于把《智营 OmniCommerce AI：电商企业级大模型运营中台》拆成可写进简历、项目介绍和面试讲解的亮点。

写简历时不要写“熟练使用 AI 技术”这种虚话，要写清楚：用了什么技术、解决了什么问题、形成了什么工程闭环、有什么可验证结果。

---

## 1. 项目总体亮点

基于 FastAPI + PostgreSQL + Redis + Qdrant + OpenSearch + MinIO 构建电商企业级大模型应用中台，覆盖商品、订单、售后、客服工单、企业知识库
RAG、Prompt 管理、模型网关、客服 Agent、导购 Agent、运营 Copilot、内容生成审核流和评测中心。

通过统一模型网关、Prompt 管理、RAG 检索、LangGraph Agent 编排、工具调用日志、评测中心和 request_id
链路追踪，形成从业务数据、模型调用、智能问答、内容生成到效果评测的完整工程闭环。

项目不是单纯调用大模型 API，而是围绕企业真实业务链路，解决模型调用不可控、Prompt 不可追踪、RAG 无法溯源、Agent
工具调用不可审计、内容生成缺少审核、评测结果无法沉淀等工程问题。

---

## 2. 后端工程架构亮点

- 基于 FastAPI 搭建企业级后端工程骨架，封装统一响应、统一异常、配置管理、结构化日志和 request_id 请求追踪机制。
- 采用 API / schemas / services / repositories / models 分层架构，避免业务逻辑堆叠在接口层，提高代码可维护性和模块复用性。
- 基于 Docker Compose 编排 PostgreSQL、Redis、MinIO、Qdrant、OpenSearch 和 FastAPI 后端，实现本地环境一键启动。
- 使用 SQLAlchemy 2.x Async + Alembic 管理数据库访问和迁移，保证数据模型演进可追踪。
- 使用 pytest + httpx 构建接口回归测试，覆盖商品、订单、售后、工单、模型网关、Prompt、RAG、Agent、内容生成和评测中心。
- 通过统一 request_id 机制，为模型调用、RAG 检索、Agent 执行、工具调用和内容审核提供链路排查基础。

可写简历版本：

> 基于 FastAPI 搭建电商 AI 中台后端工程骨架，设计统一响应、统一异常、配置管理、结构化日志和 request_id 请求追踪机制；采用
> API / schemas / services / repositories / models 分层架构，结合 Docker Compose 编排
> PostgreSQL、Redis、MinIO、Qdrant、OpenSearch 和后端服务，实现本地环境一键启动、测试和演示。

---

## 3. 数据库建模亮点

- 基于 SQLAlchemy 2.0 设计电商 + 大模型应用中台核心数据模型，覆盖用户、商品、SKU、订单、售后、工单、知识库、Prompt、模型调用日志、Agent
  执行日志、工具调用日志、评测结果和内容资产。
- 通过 Alembic 管理 PostgreSQL 数据库迁移，实现核心业务表、日志表、RAG 检索日志表、内容资产表和审核记录表的可追踪演进。
- 设计多租户字段、软删除字段、request_id 日志追踪字段，为 SaaS 化、审计追踪和可观测性打基础。
- 使用 JSONB 承载商品属性、用户偏好、订单快照、RAG 元数据、Prompt 变量 Schema、评测指标和内容审核结果，兼顾结构化查询与扩展性。
- 区分业务表和日志表：业务表保留 created_at / updated_at / deleted_at，日志表偏审计记录，强调追加写入和 request_id 追踪。

可写简历版本：

> 基于 SQLAlchemy 2.0 + Alembic 设计电商 AI 中台核心数据模型，覆盖用户、商品、订单、售后、知识库、Prompt、模型调用日志、Agent
> 执行日志、工具调用日志、评测结果和内容资产；统一设计 tenant_id、deleted_at、request_id、JSONB 扩展字段，为多租户、软删除、审计追踪和可观测性打基础。

---

## 4. 模型网关亮点

- 设计统一 ModelGateway，封装 LLM、Embedding、SSE Stream 三类模型调用能力。
- 实现 Mock Provider 和 OpenAI-compatible Provider，支持本地测试与真实模型调用解耦。
- 所有 RAG、Agent、Prompt、内容生成、评测相关模型调用统一经过 ModelGateway，禁止业务模块直连外部模型 API。
- 统一模型调用日志 model_call_log，记录
  provider、model、call_type、token、latency、status、prompt_template_id、prompt_version_id 和 request_id。
- 通过摘要存储策略避免完整 Prompt 和输出直接进入日志表，兼顾可观测性与隐私风险控制。
- 支持失败重试、错误归一化和模型供应商扩展，为后续多模型路由、成本统计和熔断降级预留空间。

可写简历版本：

> 设计统一模型网关 ModelGateway，封装 Chat、Embedding 和 SSE Stream 调用能力，实现 Mock Provider 与 OpenAI-compatible
> Provider；统一模型调用日志 model_call_log，记录 provider、model、token、latency、status、Prompt 版本和
> request_id，实现模型调用可追踪、可测试、可扩展。

---

## 5. Prompt 管理亮点

- 基于 prompt_template 和 prompt_version 实现 Prompt 模板管理、版本管理、启用 / 停用和变量渲染。
- 支持按 scene 获取当前启用 Prompt，服务客服意图识别、客服回答生成、RAG 回答生成、导购推荐、运营报告、内容生成和内容审核等场景。
- Prompt 渲染返回 template_id 和 version_id，模型调用时写入 model_call_log，实现 Prompt 版本追踪。
- 通过默认 Prompt 种子数据降低后续 Agent、RAG、内容生成模块接入成本。
- 设计变量 schema 校验，避免调用方漏传关键变量导致 Prompt 渲染失败。
- 不允许业务模块硬编码 Prompt，统一通过 PromptService 获取和渲染。

可写简历版本：

> 实现 Prompt 管理模块，支持模板、版本、场景分类、启用 / 停用和变量渲染；通过 PromptService 按 scene 获取启用版本，并将
> prompt_template_id / prompt_version_id 写入模型调用日志，实现 Prompt 调用可追踪和版本可回溯。

---

## 6. 企业知识库 RAG 亮点

- 构建企业知识库 RAG 链路，支持文档上传、MinIO 原始文件存储、多格式 Parser、OCR 抽象、文本清洗、Chunk 切分、Embedding、Qdrant
  向量检索和 OpenSearch BM25 检索。
- 设计 ParserRegistry，使 txt、md、pdf、docx、xlsx、pptx、图片等文件解析逻辑可扩展。
- 设计 OCRProvider 抽象，测试环境使用 MockOCRProvider，生产镜像预留 Tesseract OCR 能力。
- 设计 HybridRetriever 融合向量分和关键词分，并通过 CitationBuilder 生成可溯源引用。
- RAG 问答通过 PromptService 渲染 Prompt，再经 ModelGateway 调用模型，避免硬编码 Prompt 和绕过模型网关。
- 设计 rag_retrieval_log 记录 query、retrieval_mode、命中 chunk、命中文档、分数明细、耗时和 request_id，支持检索链路排查。
- 通过 Qdrant + OpenSearch 组合，兼顾语义召回和关键词精确匹配。

可写简历版本：

> 构建企业知识库 RAG 模块，支持 MinIO 文档存储、多格式解析、Chunk 切分、Embedding、Qdrant 向量检索、OpenSearch BM25 检索和引用溯源；设计
> HybridRetriever 融合语义检索与关键词检索，并通过 rag_retrieval_log 记录命中 chunk、分数明细、检索模式和 request_id，实现
> RAG
> 链路可解释、可追踪。

---

## 7. 客服 Agent 亮点

- 基于 LangGraph 构建智能客服 Agent 工作流，覆盖意图识别、订单查询、商品咨询、售后查询、售后申请、政策 RAG 问答、投诉转人工和最终回答生成。
- 将订单、商品、售后、工单、知识库能力封装为工具，工具层只调用 Service，不直接查库。
- 设计 LLM 意图识别 + 规则护栏 + 明确业务上下文优先的路由策略，避免模型误判导致错误工具调用。
- 设计高风险转人工策略，优先识别投诉、赔付、曝光、报警、律师、消协等关键词，避免完全依赖模型判断风险。
- 政策问答必须依赖 RAG citations，没有引用来源时触发谨慎处理或转人工，降低模型编造风险。
- Agent 执行写入 agent_task、agent_step_log、tool_call_log 和 model_call_log，实现可追踪执行链路。

可写简历版本：

> 基于 LangGraph 实现智能客服 Agent，覆盖订单查询、商品咨询、售后查询/申请、政策 RAG 问答和投诉转人工；设计 LLM 意图识别 +
> 规则护栏 + 工具调用 + 转人工兜底流程，并通过 agent_task、agent_step_log、tool_call_log 和 model_call_log 记录完整执行链路。

---

## 8. 导购 Agent 亮点

- 实现面向购买决策的智能导购 Agent，支持预算识别、场景识别、偏好识别、商品候选召回、SKU 对比、评价摘要和推荐理由生成。
- 推荐依据由 RecommendationService 基于真实商品、SKU、库存、价格、评价和用户偏好生成，LLM 只做表达润色，避免编造商品、价格和库存。
- 输出结构化推荐结果，包含 product_no、sku_no、sale_price、stock_quantity、review_summary、recommendation_reason 和
  match_evidence。
- match_evidence 覆盖预算匹配、场景匹配、偏好匹配、库存风险和评价风险。
- 用户指定 product_no 时优先围绕指定商品做 SKU 对比，避免 Agent 偏离用户明确意图。
- 工具调用写入 tool_call_log，便于追踪每次推荐使用了哪些规则和数据。

可写简历版本：

> 实现智能导购 Agent，支持预算、场景、偏好解析和商品推荐；通过 RecommendationService 基于真实商品、SKU、库存、价格和评价生成结构化推荐依据，LLM
> 仅用于话术润色，避免模型编造商品信息；推荐过程写入 tool_call_log，支持推荐链路追踪。

---

## 9. 运营 Copilot / SQL Guard 亮点

- 实现运营 Copilot / BI Agent，支持 GMV、订单数、客单价、库存、低库存、售后、评价等指标查询。
- 设计 MetricService 管理第一版指标口径，明确 GMV 只统计已支付订单，转化率因缺少曝光、访问、点击、加购行为数据只注册不硬算。
- 设计 SQL Guard，拦截写操作、多语句、非白名单表、缺少 tenant_id、SELECT * 和危险关键字。
- SQL 执行工具内部再次执行 Guard，避免调用方绕过安全检查直接执行 SQL。
- 限制最大返回行数，降低大结果集和敏感字段误查风险。
- 运营报告生成必须基于真实 query_result，不允许模型自由编造数据。

可写简历版本：

> 实现运营 Copilot / BI Agent，支持 GMV、订单数、库存、售后和评价等指标分析；设计 SQL Guard 对模型生成或内置 SQL
> 进行只读校验、白名单表校验、tenant_id 校验、SELECT * 拦截和最大返回行数限制，避免模型裸写 SQL 带来的安全风险。

---

## 10. 内容生成与审核流亮点

- 实现商品标题、商品卖点、商品详情页、活动文案生成，并通过 content_asset 保存内容资产和版本信息。
- 内容生成统一走 PromptService 和 ModelGateway，不硬编码 Prompt，不绕过模型网关。
- 通过 ProductService 获取商品上下文，避免内容模块直接查库造成业务口径分裂。
- 设计 ContentReviewService 执行规则审核，覆盖敏感词、绝对化营销表达、效果承诺风险、品牌名称校验、标题长度校验和竞品攻击表达。
- 设计 content_review 保存系统规则审核和人工审核动作，支持提交审核、审批通过和拒绝。
- 通过 request_id、prompt_template_id、prompt_version_id 和 model_call_log_id 关联内容资产与模型调用日志，实现内容生成链路追踪。
- 明确生成完成不等于发布，本模块只做到 approved 可发布状态，不做真实发布。

可写简历版本：

> 实现电商内容生成与审核流，支持商品标题、卖点、详情页和活动文案生成；通过 PromptService + ModelGateway 生成内容，并写入
> content_asset 版本记录；设计 content_review 记录系统规则审核和人工审核动作，实现内容生成、规则审核、人工审批和模型调用日志关联的完整闭环。

---

## 11. 评测中心亮点

- 实现评测中心模块，支持 evaluation_case / evaluation_result 管理 RAG、Agent、Prompt 和检索策略评测结果。
- 支持评测用例创建、查询、更新、归档和评测执行。
- 设计答案相关性、忠实度、上下文召回、上下文精确率、工具调用成功率、Agent 成功率等确定性评测指标。
- RAG 评测调用 KnowledgeService，Agent 评测调用真实 Agent Service，避免绕过业务链路做假评测。
- 提供评测报告、Prompt 版本对比和检索策略对比接口，为大模型应用优化提供数据基础。
- 评测失败也写入 evaluation_result，支持 success_count / failed_count 统计和问题复盘。
- 默认评测指标为确定性启发式指标，保证本地测试稳定；后续可扩展 Ragas 或 LLM-as-judge。

可写简历版本：

> 实现大模型应用评测中心，支持 RAG、Agent、Prompt 和检索策略评测；设计 evaluation_case / evaluation_result
> 数据流，支持答案相关性、忠实度、上下文召回、工具调用成功率和 Agent 成功率等指标计算，并提供评测报告与版本对比接口。

---

## 12. 可观测性亮点

- 通过 request_id 贯穿 API、模型调用、RAG 检索、Agent 执行、工具调用、内容生成和评测中心。
- 设计
  model_call_log、rag_retrieval_log、agent_task、agent_step_log、tool_call_log、evaluation_result、content_asset、content_review
  等日志和审计表。
- 输出可观测性 SQL 查询文档，支持按 request_id、Agent 类型、工具类型、评测批次和内容资产追踪问题。
- 默认 mock 测试与真实模型 smoke test 分离，保证自动化测试稳定，同时支持真实模型链路验证。
- 记录 asyncpg warning 为非阻塞已知问题，不为压 warning 破坏主业务链路。

可写简历版本：

> 设计 request_id 全链路追踪和多维日志体系，通过
> model_call_log、rag_retrieval_log、agent_task、agent_step_log、tool_call_log、evaluation_result、content_asset 和
> content_review 支撑模型调用、RAG 检索、Agent 执行、工具调用、评测和内容审核的排查与复盘。

---

## 13. 项目测试与交付亮点

- 支持 Docker Compose 一键启动本地完整依赖环境。
- 默认 pytest 使用 mock provider，避免依赖真实模型 API Key 和外部网络。
- 真实模型 smoke test 独立于默认测试，只读取本地环境变量，不硬编码 API Key。
- 提供 README、部署说明、可观测性说明、演示脚本、样例知识库和窗口交接文档。
- 当前窗口 12 接手时，全量测试已验证 117 passed，存在 1 个非阻塞 asyncpg warning。

可写简历版本：

> 完成项目最终交付收口，提供 Docker Compose 启动、环境变量说明、数据库迁移、种子数据、全量测试、真实模型 smoke test、可观测性
> SQL、演示脚本和简历亮点文档；默认测试使用 mock provider，保证自动化测试稳定，不依赖真实 API Key。

---

## 14. 面试总述话术

这个项目不是简单“接了一个大模型 API”，而是围绕电商业务场景，把基础业务服务、知识库 RAG、Prompt 管理、模型网关、Agent 编排、SQL
Guard、内容审核、评测中心和可观测性串成了一套工程闭环。

我重点解决了三类问题：

1. 业务可信：模型不能编商品、编价格、裸写 SQL 或随意处理高风险投诉。
2. 工程可信：所有模型调用、RAG 检索、Agent 工具调用都有日志和 request_id 可追踪。
3. 交付可信：项目支持 Docker Compose 启动、pytest 回归测试、真实模型 smoke test、演示脚本和可观测性查询。

如果面试官问“这个项目和普通大模型 Demo 的区别”，可以这样回答：

> 普通 Demo 往往只展示一个聊天接口或一个 RAG 问答，而这个项目把企业业务对象、Prompt 版本、模型调用、RAG 引用、Agent 工具调用、SQL
> 安全、内容审核、评测结果和可观测性都落到了正式工程结构里。它不是只追求模型回答像不像，而是关注企业系统里更关键的可控、可追踪、可测试和可交付。

---

## 15. 简历精简版项目描述

可以直接放进简历的版本：

> 智营 OmniCommerce AI：电商企业级大模型运营中台  
> 基于 FastAPI、PostgreSQL、Redis、Qdrant、OpenSearch、MinIO 和 Docker Compose 构建电商 AI 中台，覆盖商品、订单、售后、知识库
> RAG、Prompt 管理、模型网关、客服 Agent、导购 Agent、运营 Copilot、内容生成审核流和评测中心。设计统一
> ModelGateway、PromptService、HybridRetriever、LangGraph Agent 工作流、SQL Guard、内容审核流和 evaluation_result 评测闭环，并通过
> request_id、model_call_log、rag_retrieval_log、agent_task、tool_call_log 等日志表实现全链路可观测。默认测试使用 mock
> provider，支持 Docker Compose 一键启动、pytest 回归测试和真实模型 smoke test。

## v1.1 认证 / RBAC / 租户隔离生产化增强

- 新增轻量认证体系，设计 `auth_account` 登录账号表，与 `user_profile` 业务用户画像解耦，避免将登录凭证、角色状态混入业务画像模型。
- 基于 PBKDF2-HMAC-SHA256 实现密码 hash 存储，避免明文密码落库；基于 HS256 JWT 实现登录态签发与解析，claims
  包含 `user_id`、`user_no`、`tenant_id`、`role`、`exp`。
- 设计 `get_current_user`、`get_current_tenant_id`、`require_roles(...)` 权限依赖，支持 `admin / operator / viewer` 三类角色。
- 在认证模式下从 JWT 注入 `request.state.user_id` 和 `request.state.tenant_id`，并校验请求 `tenant_id` 与
  token `tenant_id` 是否一致，补齐多租户隔离边界。
- 采用 `AUTH_ENABLED=false / true` 双模式设计：默认关闭强制认证，保证旧测试和旧演示兼容；开启后展示生产化登录、RBAC 和租户隔离能力。
- 将 RBAC 接入 Prompt 写接口、Knowledge 上传、Content 审批 / 驳回、Evaluation 执行等关键高风险操作，避免大面积重构客服、导购、运营
  Copilot 主链路。
- 完成 `.gitignore`、`backend/.env.example`、Docker Compose 环境变量映射和 API Key / JWT secret
  安全治理，确保真实密钥只通过本地环境变量注入，不进入代码仓库。
- 新增 Auth / RBAC 自动化测试：默认兼容模式全量回归 `130 passed, 4 skipped, 1 warning`；认证模式下 `test_rbac_api.py` 验证
  RBAC 与 tenant mismatch 拦截 `4 passed`。

可沉淀到简历的一句话：

> 为电商 AI 中台补充轻量生产化身份体系，基于 JWT、PBKDF2 密码 hash、三角色 RBAC 和 tenant_id token
> 注入实现认证、权限控制和租户隔离；通过 `AUTH_ENABLED` 双模式兼容旧演示与生产化认证演示，并将权限拦截接入
> Prompt、知识库、内容审批和评测执行等关键高风险接口。
