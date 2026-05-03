# 执行窗口 6 最终交接文档：企业知识库 RAG 模块

## 一、窗口基本信息

| 项目         | 内容                                         |
|------------|--------------------------------------------|
| 窗口编号       | 执行窗口 6                                     |
| 模块名称       | 企业知识库 RAG / Knowledge Base RAG             |
| 最终状态       | 已完成 6A 主链路 + 6B 企业级增强                      |
| 是否建议进入窗口 7 | 是                                          |
| 下游建议窗口     | 客服 Agent / 导购 Agent / 运营 Copilot 等上层智能应用窗口 |
| 当前测试状态     | 本地全量测试 `60 passed`，容器内全量测试 `60 passed`     |

---

## 二、窗口目标

执行窗口 6 的目标是完成企业知识库 RAG 能力建设，支持企业文档上传、解析、切片、Embedding、向量入库、关键词检索、混合检索、引用溯源、Prompt
管理和模型网关回答生成。

最终链路如下：

```text
文档上传
  ↓
MinIO 保存原始文件
  ↓
ParserRegistry 选择 Parser
  ↓
ParsedDocument / ParsedSection / ParsedTable 统一解析输出
  ↓
TextCleaner 文本清洗
  ↓
TextChunker 切片
  ↓
PostgreSQL 写入 knowledge_document / knowledge_chunk
  ↓
KeywordExtractor 生成 keywords_json
  ↓
ModelGateway 生成 Embedding
  ↓
Qdrant 写入向量
  ↓
OpenSearch 写入 chunk 关键词索引
  ↓
HybridRetriever 混合检索
    ↓
    Qdrant Vector Search
    ↓
    OpenSearch BM25 Search
  ↓
NoopReranker 排序占位
  ↓
RagContextBuilder 组装上下文
  ↓
CitationBuilder 生成引用来源
  ↓
RagRetrievalLog 写入检索日志
  ↓
PromptService 渲染 rag_answer_generation Prompt
  ↓
ModelGateway.chat 生成回答
  ↓
返回 answer + citations
```

本窗口没有做：

- 客服 Agent；
- 导购 Agent；
- 运营 Copilot；
- ModelGateway 重构；
- Prompt 管理重构；
- 已有业务 API 重构。

---

## 三、最终完成能力

| 能力                                        | 最终状态                            |
|-------------------------------------------|---------------------------------|
| 文档上传                                      | 已完成                             |
| MinIO 原始文件存储                              | 已完成                             |
| `storage_object_key` 写入                   | 已完成                             |
| Parser 抽象                                 | 已完成                             |
| `ParserRegistry`                          | 已完成                             |
| 多格式文档解析                                   | 已完成                             |
| `OCRProvider` 抽象                          | 已完成                             |
| OCR 生产依赖                                  | 已完成                             |
| 测试默认 `MockOCRProvider`                    | 已保持                             |
| Chunk 切片                                  | 已完成                             |
| `keywords_json` 生成                        | 已完成                             |
| Embedding                                 | 已接 `ModelGateway`               |
| Qdrant 向量入库                               | 已完成                             |
| `OpenSearchKeywordStore`                  | 已完成                             |
| OpenSearch chunk 索引写入                     | 已完成                             |
| BM25 / match 检索                           | 已完成                             |
| `tenant_id` / `status` / `document_id` 过滤 | 已支持                             |
| `HybridRetriever`                         | 已完成，主逻辑未被 6B 推翻                 |
| Reranker                                  | 当前 `NoopReranker`，预留真实 reranker |
| ContextBuilder                            | 已完成                             |
| CitationBuilder                           | 已完成                             |
| `PromptService` 接入                        | 已完成                             |
| `ModelGateway.chat` 接入                    | 已完成                             |
| RAG 检索日志                                  | 已完成                             |
| 本地全量测试                                    | `60 passed`                     |
| 容器内全量测试                                   | `60 passed`                     |

容器内最终测试结果为：

```text
60 passed in 5.59s
```

并且 Tesseract OCR 生产依赖已安装，语言包包含：

```text
chi_sim
eng
osd
```

---

## 四、最终 API 接口

---

### 4.1 上传知识库文档

```http
POST /api/v1/knowledge/documents/upload
```

请求类型：

```text
multipart/form-data
```

字段：

| 字段          | 类型         | 必填 | 说明            |
|-------------|------------|----|---------------|
| `tenant_id` | UUID       | 是  | 租户 ID         |
| `file`      | UploadFile | 是  | 上传文件          |
| `title`     | string     | 否  | 文档标题          |
| `language`  | string     | 否  | 默认 `zh-CN`    |
| `user_id`   | UUID       | 否  | 当前认证未完成前可显式传入 |

上传后会完成：

- MinIO 原始文件保存；
- 文档解析；
- Chunk 切片；
- PostgreSQL 入库；
- Embedding；
- Qdrant 入库；
- OpenSearch 索引写入；
- `document.status = indexed`；
- `parser_status = success`。

---

### 4.2 查询知识库文档列表

```http
GET /api/v1/knowledge/documents
```

参数：

| 参数          | 类型     | 必填 | 说明    |
|-------------|--------|----|-------|
| `tenant_id` | UUID   | 是  | 租户 ID |
| `page`      | int    | 否  | 页码    |
| `page_size` | int    | 否  | 每页数量  |
| `status`    | string | 否  | 文档状态  |
| `keyword`   | string | 否  | 标题关键词 |

---

### 4.3 知识库混合检索

```http
POST /api/v1/knowledge/search
```

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "query": "七天无理由退货需要满足什么条件？",
  "top_k": 5
}
```

返回重点字段：

```text
query
items
  document_id
  document_title
  chunk_id
  chunk_no
  page_no
  section_title
  score
  vector_score
  keyword_score
  content_snippet
  metadata_json
```

当前最终检索模式：

```text
hybrid_opensearch
```

即：

```text
Qdrant Vector Search + OpenSearch BM25 Search
```

---

### 4.4 知识库 RAG 问答

```http
POST /api/v1/knowledge/ask
```

请求示例：

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "question": "七天无理由退货有哪些条件？",
  "top_k": 5
}
```

返回重点字段：

```text
question
answer
citations
prompt_template_id
prompt_version_id
```

引用来源 `citations` 包含：

```text
document_id
document_title
chunk_id
chunk_no
page_no
section_title
score
content_snippet
```

最终验证中，`/knowledge/search` 和 `/knowledge/ask` 均正常返回，且检索日志已分别记录 `search` 和 `ask` 两类来源。

---

## 五、文档解析能力

### 5.1 Parser 抽象

核心对象：

```text
DocumentParser
ParserRegistry
ParsedDocument
ParsedSection
ParsedTable
```

设计原则：

- `KnowledgeService` 不关心具体文件格式；
- `KnowledgeService` 不写死 `.txt / .pdf / .docx` 判断；
- `ParserRegistry` 负责根据 `filename / mime_type` 选择 Parser；
- 所有 Parser 输出统一 `ParsedDocument`。

---

### 5.2 支持格式

| 格式                    | 当前能力                                          |
|-----------------------|-----------------------------------------------|
| `.txt`                | 支持 UTF-8 / UTF-8 BOM / GB18030                |
| `.md / .markdown`     | 按文本解析，保留 Markdown 内容                          |
| `.pdf`                | 文本型 PDF 提取文本；扫描页可走 OCR                        |
| `.docx`               | 段落 + 基础表格                                     |
| `.xlsx`               | 多 Sheet，记录 `sheet_name / row_start / row_end` |
| `.pptx`               | 按 slide 提取标题、正文、备注                            |
| `.png / .jpg / .jpeg` | 通过 `OCRProvider` 提取文本                         |
| 扫描版 PDF               | 无文本页可走 `OCRProvider`                          |

---

### 5.3 表格处理

当前支持：

- DOCX 基础表格转 Markdown；
- XLSX Sheet 转结构化 Markdown / 文本；
- `ParsedTable.to_markdown()`；
- 表格内容进入 chunk。

允许降级：

- 复杂表格；
- 扫描表格；
- 跨页表格。

降级信息通过以下字段记录：

```text
metadata.parser_quality
```

---

## 六、OCR 设计

新增 OCR 抽象：

```text
OCRProvider
OCRResult
MockOCRProvider
TesseractOCRProvider
```

当前策略：

- 测试环境默认 `MockOCRProvider`；
- pytest 不依赖真实 OCR；
- 生产镜像已安装 `tesseract-ocr` 和中文语言包。

Docker 内已验证：

```text
tesseract 5.5.0
chi_sim
eng
osd
```

该结果来自容器内：

```bash
tesseract --version
tesseract --list-langs
```

注意：

```text
OCR_PROVIDER 当前默认 mock
如需生产启用真实 OCR，可后续通过 OCR_PROVIDER=tesseract 配置化切换
```

---

## 七、MinIO 文档对象存储

### 7.1 新增能力

新增：

```text
MinIOStorageClient
StoredObject
```

文件：

```text
backend/app/storage/__init__.py
backend/app/storage/minio_storage.py
```

能力：

- 自动创建 bucket；
- 上传原始文件 bytes；
- 返回 `bucket / object_key / size / content_type`；
- 失败时 best-effort 删除对象。

---

### 7.2 当前存储路径

上传文件后：

```text
knowledge_document.storage_object_key = knowledge/{tenant_id}/{uuid}_{filename}
```

metadata 中写入：

```json
{
  "storage": {
    "provider": "minio",
    "bucket": "omni-knowledge",
    "object_key": "knowledge/...",
    "size": 361,
    "content_type": "text/markdown"
  }
}
```

---

### 7.3 一致性说明

MinIO 和 PostgreSQL 不在同一个事务系统内。

当前策略：

```text
MinIO 上传成功
如果后续数据库 / Qdrant / OpenSearch 失败
则执行 best-effort cleanup 删除对象
```

后续增强建议：

- outbox 事件表；
- 孤儿对象定时清理；
- 对象状态字段。

---

## 八、Embedding 与 Qdrant

### 8.1 Embedding

Embedding 通过：

```text
RagEmbedder
ModelGateway.embeddings()
```

完成。

不允许 RAG 模块直接调用外部模型 API。

---

### 8.2 Qdrant

向量库：

```text
QdrantVectorStore
```

当前 collection：

```text
omni_knowledge_chunks
```

当前向量维度：

```text
RAG_VECTOR_SIZE=3
```

说明：

```text
当前 mock embedding 输出 3 维向量
后续切真实 embedding 模型时必须同步调整 RAG_VECTOR_SIZE
```

---

## 九、OpenSearchKeywordStore

### 9.1 新增能力

新增：

```text
OpenSearchKeywordStore
```

保留：

```text
KeywordStore 抽象
SimpleKeywordStore fallback
```

`OpenSearchKeywordStore` 支持：

- `ensure_index()`
- `upsert_chunks()`
- `search()`
- BM25 / match 检索
- `tenant_id` 过滤
- `document_status` 过滤
- `document_id` 过滤

---

### 9.2 HybridRetriever 主逻辑未改

6B 没有重写 `HybridRetriever`。

实现方式：

```text
HybridRetriever 继续依赖 KeywordStore.search()
6B 新增 OpenSearchKeywordStore
KnowledgeService 装配层改为 OpenSearchKeywordStore
```

这满足总控要求：

```text
HybridRetriever 不能改主逻辑，只能通过 KeywordStore 抽象替换实现
```

---

### 9.3 OpenSearch 索引内容

写入 OpenSearch 的字段包括：

```text
tenant_id
document_id
document_no
document_title
document_status
chunk_id
chunk_no
content
keywords
page_no
section_title
metadata_json
created_at
```

当前 index：

```text
omni_knowledge_chunks
```

已验证：

- OpenSearch index 自动创建；
- `_count = 1`；
- BM25 检索命中“七天无理由退货”；
- `tenant_id / document_status` 过滤生效。

业务检索结果中，top1：

```text
keyword_score = 1.0
vector_score = 1.0
score = 1.0
```

说明 OpenSearch 关键词检索已经参与混合检索。

---

## 十、Hybrid Retrieval

最终检索流程：

```text
query
  ↓
RagEmbedder 生成 query embedding
  ↓
QdrantVectorStore.search()
  ↓
OpenSearchKeywordStore.search()
  ↓
HybridRetriever 合并 chunk_id
  ↓
分数归一化
  ↓
vector_weight / keyword_weight 加权
  ↓
NoopReranker 排序
```

当前权重：

```text
RAG_VECTOR_WEIGHT=0.65
RAG_KEYWORD_WEIGHT=0.35
```

当前 retrieval mode：

```text
hybrid_opensearch
```

---

## 十一、RAG 检索日志

### 11.1 新增表

新增表：

```text
rag_retrieval_log
```

新增 model：

```text
backend/app/models/rag.py
```

新增 repository：

```text
backend/app/repositories/rag_retrieval_log_repository.py
```

新增 migration：

```text
backend/alembic/versions/6b01_add_rag_retrieval_log.py
```

---

### 11.2 字段

```text
id
tenant_id
user_id
request_id
query
retrieval_mode
top_k
result_count
retrieved_chunk_ids
retrieved_document_ids
vector_score
keyword_score
final_score
scores_json
latency_ms
metadata_json
created_at
```

---

### 11.3 记录内容

`KnowledgeService.search()` 和 `KnowledgeService.ask()` 都会写入检索日志。

记录内容包括：

- `query`
- `retrieval_mode`
- `retrieved_chunk_ids`
- `retrieved_document_ids`
- top1 `vector_score`
- top1 `keyword_score`
- top1 `final_score`
- 全部命中 `scores_json`
- `latency_ms`
- `request_id`
- `tenant_id`
- `source = search / ask`
- `retriever = HybridRetriever`
- `reranker = NoopReranker`
- `vector_store = QdrantVectorStore`
- `keyword_store = OpenSearchKeywordStore`

当前日志中已验证两条记录：

```text
source = search
source = ask
retrieval_mode = hybrid_opensearch
result_count = 5
vector_score = 1
keyword_score = 1
final_score = 1
```

并且 `scores_json` 已记录每个 chunk 的：

```text
vector_score
keyword_score
final_score
```

---

## 十二、Prompt 与 ModelGateway

### 12.1 Prompt

RAG 问答使用：

```text
scene = rag_answer_generation
```

调用方式：

```text
PromptService.render_prompt()
```

不在 `KnowledgeService` 中硬编码 Prompt。

---

### 12.2 ModelGateway

Embedding：

```text
ModelGateway.embeddings()
```

Chat：

```text
ModelGateway.chat()
```

模型调用日志已能记录 embedding 和 chat 调用。

---

## 十三、新增 / 修改文件清单

### 13.1 新增文件

```text
backend/app/storage/__init__.py
backend/app/storage/minio_storage.py

backend/app/models/rag.py
backend/app/repositories/rag_retrieval_log_repository.py
backend/alembic/versions/6b01_add_rag_retrieval_log.py

backend/tests/test_rag_retrieval_log.py
backend/tests/test_storage_minio.py
```

6A 阶段新增的核心文件继续保留：

```text
backend/app/schemas/knowledge.py
backend/app/repositories/knowledge_repository.py
backend/app/services/knowledge_service.py
backend/app/api/v1/knowledge.py

backend/app/rag/text_cleaner.py
backend/app/rag/chunker.py
backend/app/rag/keyword_extractor.py
backend/app/rag/embedder.py
backend/app/rag/vector_store.py
backend/app/rag/keyword_store.py
backend/app/rag/retriever.py
backend/app/rag/reranker.py
backend/app/rag/context_builder.py
backend/app/rag/citation.py
backend/app/rag/answer_generator.py

backend/app/rag/parsers/base.py
backend/app/rag/parsers/registry.py
backend/app/rag/parsers/text_parser.py
backend/app/rag/parsers/pdf_parser.py
backend/app/rag/parsers/docx_parser.py
backend/app/rag/parsers/xlsx_parser.py
backend/app/rag/parsers/pptx_parser.py
backend/app/rag/parsers/image_parser.py

backend/app/rag/ocr/base.py
backend/app/rag/ocr/mock.py
backend/app/rag/ocr/tesseract.py

backend/tests/test_rag_parsers.py
backend/tests/test_rag_chunker.py
backend/tests/test_rag_office_parsers.py
```

---

### 13.2 修改文件

```text
docker-compose.yml
backend/Dockerfile
backend/pyproject.toml
backend/.env.example
backend/app/core/config.py
backend/app/core/exceptions.py
backend/app/models/__init__.py
backend/app/api/v1/router.py
backend/app/rag/keyword_store.py
backend/app/services/knowledge_service.py
backend/tests/test_prompt_api.py
```

---

## 十四、配置项

### 14.1 OpenSearch

```env
OPENSEARCH_URL=http://opensearch:9200
OPENSEARCH_INDEX=omni_knowledge_chunks
OPENSEARCH_USERNAME=
OPENSEARCH_PASSWORD=
```

宿主机访问：

```text
http://127.0.0.1:9200
```

---

### 14.2 MinIO

```env
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=omni_minio
MINIO_SECRET_KEY=omni_minio_password
MINIO_BUCKET_KNOWLEDGE=omni-knowledge
MINIO_SECURE=false
```

宿主机访问：

```text
S3 API: http://127.0.0.1:9000
Console: http://127.0.0.1:9001
```

账号：

```text
omni_minio
```

密码：

```text
omni_minio_password
```

---

### 14.3 OCR

```env
OCR_PROVIDER=mock
```

说明：

- 生产依赖已具备；
- 测试默认 mock；
- pytest 不依赖真实 OCR。

---

### 14.4 RAG

```env
RAG_VECTOR_COLLECTION=omni_knowledge_chunks
RAG_VECTOR_SIZE=3
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=80
RAG_TOP_K=5
RAG_VECTOR_WEIGHT=0.65
RAG_KEYWORD_WEIGHT=0.35
RAG_RERANK_TOP_N=5
```

---

## 十五、Alembic migration 说明

新增 migration：

```text
6b01_add_rag_retrieval_log
```

用途：

```text
创建 rag_retrieval_log 表
```

执行：

```bash
cd D:\omni-commerce-ai\backend
python -m alembic upgrade head
```

验证：

```bash
python -m alembic current
```

预期：

```text
6b01_add_rag_retrieval_log (head)
```

---

## 十六、验证方式

### 16.1 OpenSearch

```bash
curl.exe "http://127.0.0.1:9200"
curl.exe "http://127.0.0.1:9200/_cluster/health"
curl.exe "http://127.0.0.1:9200/_cat/indices?v"
curl.exe "http://127.0.0.1:9200/omni_knowledge_chunks/_count"
```

BM25 检索：

```powershell
curl.exe -X POST "http://127.0.0.1:9200/omni_knowledge_chunks/_search" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_opensearch_query.json"
```

预期：

```text
hits.total.value >= 1
tenant_id 过滤生效
document_status = indexed
content 命中业务文档
```

---

### 16.2 MinIO

```bash
curl.exe "http://127.0.0.1:9000/minio/health/live"
```

数据库验证：

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select document_no, title, storage_object_key, metadata_json->'storage' as storage from knowledge_document order by created_at desc limit 5;"
```

预期：

```text
storage_object_key = knowledge/...
metadata_json.storage.provider = minio
metadata_json.storage.bucket = omni-knowledge
```

---

### 16.3 RAG 检索日志

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select query, retrieval_mode, result_count, vector_score, keyword_score, final_score, latency_ms, request_id, created_at from rag_retrieval_log order by created_at desc limit 10;"
```

明细：

```bash
docker compose exec postgres psql -U omni -d omni_ai -c "select retrieved_chunk_ids, scores_json, metadata_json from rag_retrieval_log order by created_at desc limit 3;"
```

预期：

```text
retrieval_mode = hybrid_opensearch
result_count >= 1
vector_score / keyword_score / final_score 已记录
scores_json 已记录每个 chunk 分数
metadata_json.keyword_store = OpenSearchKeywordStore
```

---

### 16.4 OCR 生产依赖

```bash
docker compose exec backend tesseract --version
docker compose exec backend tesseract --list-langs
```

预期：

```text
chi_sim
eng
osd
```

---

### 16.5 RAG 主接口

```powershell
curl.exe -X POST "http://127.0.0.1:8002/api/v1/knowledge/search" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_knowledge_search.json"
```

```powershell
curl.exe -X POST "http://127.0.0.1:8002/api/v1/knowledge/ask" `
  -H "Content-Type: application/json" `
  --data-binary "@tmp_knowledge_ask.json"
```

预期：

```text
search success = true
search 返回 vector_score / keyword_score / score
ask success = true
ask 返回 answer / citations / prompt_template_id / prompt_version_id
```

---

## 十七、测试结果

### 17.1 本地全量测试

```bash
cd D:\omni-commerce-ai\backend
python -m pytest tests/
```

结果：

```text
60 passed
```

---

### 17.2 容器内全量测试

```bash
cd D:\omni-commerce-ai
docker compose exec backend python -m pytest tests/
```

结果：

```text
60 passed in 5.59s
```

容器内测试覆盖：

- aftersales
- exceptions
- health
- llm_api
- llm_gateway
- middleware
- orders
- products
- prompt_api
- prompt_service
- rag_chunker
- rag_office_parsers
- rag_parsers
- rag_retrieval_log
- response
- storage_minio
- tickets

容器内测试日志已验证全部 60 个用例通过。

---

## 十八、已知问题与后续建议

### 18.1 OpenSearch 中文分词仍可增强

当前 OpenSearch 使用默认 analyzer，可完成基础 BM25 / match 检索。

后续建议：

- 接入 IK Analyzer 或合适中文 analyzer；
- 为 `content / document_title / section_title` 配置中文分词；
- `keywords` 字段继续保留 keyword 类型。

---

### 18.2 MinIO 与 PostgreSQL 暂非强事务

当前使用 best-effort cleanup。

后续建议：

- outbox 事件表；
- 孤儿对象清理任务；
- 对象状态字段。

---

### 18.3 Reranker 当前仍为 `NoopReranker`

当前只是按融合分排序。

后续建议：

- 接 `bge-reranker`；
- 或通过 `ModelGateway` 接 rerank provider；
- 保持 `Reranker` 接口不变。

---

### 18.4 RAG 检索日志明细当前使用 JSONB

当前：

```text
rag_retrieval_log.scores_json
```

记录每个 chunk 分数明细。

后续如果评测中心需要逐 chunk SQL 分析，可以拆成：

```text
rag_retrieval_log
rag_retrieval_log_item
```

当前阶段 JSONB 更轻量，足够支撑审计和排查。

---

### 18.5 OCR Provider 切换可进一步配置化

当前 Docker 已安装真实 OCR 依赖，但默认 Mock。

后续建议：

```env
OCR_PROVIDER=tesseract
OCR_LANG=chi_sim+eng
```

并让 `ParserRegistry` 根据 `OCR_PROVIDER` 构造 `OCRProvider`。

---

### 18.6 本地 httpx 代理问题

Windows / Conda 环境中，`httpx` 可能读取系统代理，导致 localhost 请求返回 `502`。

本地测试前建议：

```powershell
$env:NO_PROXY="127.0.0.1,localhost"
$env:no_proxy="127.0.0.1,localhost"

Remove-Item Env:\HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:\HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:\ALL_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:\http_proxy -ErrorAction SilentlyContinue
Remove-Item Env:\https_proxy -ErrorAction SilentlyContinue
Remove-Item Env:\all_proxy -ErrorAction SilentlyContinue
```

后续建议：

```python
trust_env = False
```

统一放到测试 helper 中。

---

## 十九、交付结论

执行窗口 6 最终交付完成。

最终实现不是一个简单 RAG demo，而是一个具备企业级扩展边界的知识库模块：

- `ParserRegistry` 负责多格式解析扩展；
- `OCRProvider` 保证 OCR 可插拔；
- MinIO 保存原始文档；
- PostgreSQL 保存文档和 chunk 元数据；
- Qdrant 负责向量检索；
- OpenSearch 负责关键词 / BM25 检索；
- `HybridRetriever` 负责融合检索；
- `CitationBuilder` 负责引用溯源；
- `RagRetrievalLog` 负责检索审计；
- `PromptService` 负责 Prompt 管理；
- `ModelGateway` 负责 Embedding 和 Chat 调用。

建议正式进入执行窗口 7，开始建设客服 Agent、导购 Agent、运营 Copilot 等上层智能应用能力。