# 课程资料 RAG 问答系统

基于 FastAPI + MySQL + 大语言模型的课程资料问答系统。上传 TXT、PDF、DOCX 资料后自动分块入库，提问时通过混合检索与重排序找出相关资料片段，交给模型生成带来源引用的回答，并支持多轮对话、问答历史与文档管理。

## 功能

- 多格式上传：支持 TXT、PDF、DOCX（扫描版 PDF 会给出明确提示）
- 分块存储：固定长度 200 字、重叠 40 字自动分块
- 同名覆盖：默认拒绝（409），前端确认后带 `overwrite=true` 强制覆盖
- 文档管理：查看文档列表、删除文档（连带删除资料块与向量缓存）
- RAG 问答：BM25 + 向量语义混合检索海选 Top-20，CrossEncoder 重排序精选 Top-5
- 向量缓存：资料向量持久化到 `chunk_embeddings` 表，提问时无需重复编码全部资料
- 多轮对话：通过 `session_id` 保存会话，历史问答作为上下文传给模型
- 回答附带来源：每条引用包含文件名、相关度分数与原文片段
- 问答历史：分页查看全部记录
- 前端交互：复制回答、导出对话（Markdown）、新对话、加载与错误状态
- 网页界面 + Swagger 调试接口

## 技术栈

- 后端：FastAPI、Uvicorn
- 数据库：MySQL 8（`mysql-connector-python`）
- AI：OpenAI 兼容 API（通过 `openai` SDK 调用）
- 检索：`sentence-transformers`（bge-small-zh 向量模型 + bge-reranker-base 重排序模型）
- 关键词检索：BM25（`rank_bm25`）
- 配置：`python-dotenv`
- 前端：原生 HTML + CSS + JavaScript（`fetch`）

## 目录结构

```text
app/
  main.py             FastAPI 应用、网页、上传、问答、历史接口
  database.py         所有 MySQL 读写函数
  rag.py              检索调用、提示词组装、模型调用
  document_parser.py  TXT / PDF / DOCX 解析器
  vector_search.py    向量缓存、混合检索、重排序
  schemas/question.py 请求数据模型
demo_app/             独立完整示例（供参考）
data/                 示例资料
docs/                 文档与计划
```

## 快速开始（Docker 推荐）

需要先安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

1. 克隆仓库并进入目录：

```bash
git clone https://github.com/buoluonei/course_rag.git
cd course_rag
```

> 后续命令都要在包含 `docker-compose.yml` 的项目根目录里执行。

2. 复制配置模板并填写：

```bash
cp .env.example .env
```

打开 `.env` 填写：

- `COURSE_DB_PASSWORD`：随便填，Docker 会用这个密码自动创建 MySQL
- `COURSE_LLM_BASE_URL` / `COURSE_LLM_MODEL` / `COURSE_LLM_API_KEY`：你自己的模型接口信息

> 没有 API Key 也能启动系统、上传资料，但提问不会回答。

3. 启动：

```bash
docker compose up -d --build
```

4. 打开 <http://localhost:8000/> 即可使用。

> MySQL 首次启动需要初始化（自动建库建表），如果页面暂时提示数据库错误，等十几秒再刷新。首次构建需要下载 PyTorch 与模型依赖，耗时较长属正常现象；模型首次加载会访问 Hugging Face，可设置 `HF_ENDPOINT=https://hf-mirror.com` 加速。

## 环境准备（本地开发）

1. 安装依赖：

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. 复制配置模板并填写 `.env`，然后初始化数据库：

```bash
mysql -u root -p < db_init.sql
```

脚本会创建 `course_rag` 数据库和 `documents`、`chunks`、`questions`、`chunk_embeddings` 四张表。

3. 启动服务：

```bash
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- 网页：<http://127.0.0.1:8000/>
- Swagger：<http://127.0.0.1:8000/docs>

## 主要接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /health | 健康检查 |
| POST | /documents/upload?overwrite=true/false | 上传 TXT / PDF / DOCX，同名默认 409 |
| GET | /documents | 文档列表 |
| DELETE | /documents/{id} | 删除文档及其资料块 |
| POST | /answers | 提问（可带 session_id 实现多轮） |
| GET | /questions?limit=&offset= | 问答历史分页 |
| GET | /questions/{id} | 单条问答 |
| DELETE | /questions/{id} | 删除问答 |
| GET | /sessions/{session_id} | 导出指定会话的问答记录 |
| GET | /search?keyword= | 关键词搜索资料片段 |

## 关键实现

- **分块**：`split_chunks` 固定 200 字、重叠 40 字，参数通过 `CHUNK_SIZE` / `CHUNK_OVERLAP` 常量配置；分块大小经过评测对比（100/200/300/500 字），200 字在召回与精度上综合最优
- **混合检索**：BM25 关键词排名与 BGE 向量语义排名通过 RRF 融合，海选 Top-20，兼顾关键词命中与语义相近
- **重排序**：CrossEncoder 对候选逐条打分，精选 Top-5 作为模型上下文
- **向量缓存**：资料上传/删除后自动重建 `chunk_embeddings`，资料清空时同步清理旧缓存
- **模型懒加载**：向量模型与重排序模型在首次使用时才加载，应用启动和健康检查不受模型初始化拖累
- **异常处理**：数据库、检索模型、模型 API 故障统一转换为 503，并保留原始异常链便于排查
- **多轮对话**：按 `session_id` 读取历史问答，组装为 `user/assistant` 消息再调用模型
- **安全**：所有 SQL 使用参数化查询；网页渲染用户内容使用 `textContent` 防止 XSS；上传限制 10MB

## 检索评测

项目基于小型标注集，用 Recall@5 与 MRR 对比四类检索方法：

```text
BM25 / 向量检索 / 混合检索 / 混合 + 重排序
```

评测结果显示：混合 + 重排序在召回（Recall@5）与排名质量（MRR）上均优于单一方法，这也是生产链路采用该方案的原因。
