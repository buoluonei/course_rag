# 课程资料 RAG 问答系统

基于 FastAPI、MySQL 和大模型接口的课程资料问答项目。上传课程资料后，系统提取文本并切分；提问时检索相关片段，再请模型结合资料回答。页面支持查看文档、发起对话和查看问答记录。

## 功能与流程

- 上传 UTF-8 编码的 TXT、可提取文字的 PDF 和 DOCX，单文件上限 10 MiB；同名文档默认拒绝覆盖，可确认后覆盖。
- 按段落、标题和 PDF 页码组织文本；较长文本使用最多 200 字、重叠 40 字的滑动窗口切分。短段落会合并，不保证所有相邻片段均有重叠。
- 将 BM25 关键词排名与 BGE 向量语义排名通过 RRF 融合，选取最多 20 个候选片段，再用 CrossEncoder 重排序，选取最多 5 个片段作为上下文。
- 使用 OpenAI 兼容的模型服务回答，返回候选片段及其文件名、片段编号、章节、页码（如有）和重排序分数。
- 将文档片段、问答与会话 ID 保存在 MySQL，支持文档管理、历史记录和按会话读取问答。

```text
上传文件 → 文本解析与切分 → MySQL 保存片段
用户提问 → BM25 + 语义检索 → RRF 融合 → 重排序 → 模型生成 → 保存问答
```

返回的来源是提供给模型的候选片段，不能保证每个片段都被回答实际采用；模型也可能出现事实错误。向量缓存与现有片段 ID 不一致时，当前实现会在查询时重新编码片段，这一回退过程不会自动写入缓存。检索模型在首次使用时加载，初次运行可能需要下载模型。

## 环境与配置

- Docker Desktop / Docker Engine（含 Compose），或 Python 3.11 与 MySQL 8。
- 可访问的 OpenAI 兼容模型接口、模型名称和 API Key；模型调用可能产生费用。
- 首次运行需要能访问 Hugging Face 或已配置的镜像，以下载 `BAAI/bge-small-zh-v1.5` 和 `BAAI/bge-reranker-base`。

复制配置模板：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，设置 `COURSE_DB_PASSWORD`、`COURSE_LLM_BASE_URL`、`COURSE_LLM_MODEL` 和 `COURSE_LLM_API_KEY`。本地运行时可通过 `COURSE_DB_HOST` 指定数据库地址；Compose 将应用的数据库地址设置为 `db`。`HF_ENDPOINT` 可按网络环境配置。不要把 `.env` 或真实密钥提交到仓库。

## Docker 启动

在项目根目录执行：

```powershell
docker compose up -d --build
docker compose logs -f app
```

构建完成后访问 <http://127.0.0.1:8000/>，接口文档位于 <http://127.0.0.1:8000/docs>。上传资料后即可尝试问答。MySQL 首次启动时会执行 `db_init.sql`；数据库尚未就绪时请求可能失败，可以稍后重试。初始化脚本仅在 MySQL 数据目录首次初始化时自动执行，已有数据卷不会因修改脚本而自动迁移。

MySQL 数据保存在 Compose 的 `db_data` 卷。普通停止命令为 `docker compose down`；`docker compose down -v` 会同时删除数据卷。上传内容、问答历史和模型配置应按实际情况另行备份。

## 本地启动

先准备 MySQL 8，并执行 `db_init.sql` 创建数据库和数据表，再填写 `.env`。在 Windows PowerShell 中：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Linux / macOS 可使用 `.venv/bin/python`。已有旧数据库时，`CREATE TABLE IF NOT EXISTS` 不会自动添加新字段，需检查数据库结构与当前 `db_init.sql` 一致。

## 接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/livez` | 应用进程存活检查 |
| GET | `/readyz` | 检查数据库连接 |
| POST | `/documents/upload` | 上传资料，可用 `overwrite=true` 覆盖同名文件 |
| GET / DELETE | `/documents` / `/documents/{id}` | 查看或删除文档 |
| POST | `/answers` | 提问，可提供 `session_id` 关联历史 |
| GET | `/questions` | 分页读取问答历史 |
| GET / DELETE | `/questions/{id}` | 读取或删除单条问答 |
| GET | `/sessions/{session_id}` | 读取指定会话的问答 |
| GET | `/search?keyword=...` | 根据关键词查找片段 |

## 项目结构

```text
app/main.py             页面与 API 路由
app/static/             页面、样式和交互脚本
app/document_parser.py  TXT、PDF、DOCX 文本解析
app/chunking.py         文档块与片段生成
app/vector_search.py    混合检索、向量缓存与重排序
app/rag.py              检索上下文组装与模型调用
app/database.py         MySQL 读写
db_init.sql             数据库初始化脚本
tests/                  单元测试
demo_app/               独立示例
```

## 测试与评估

安装依赖后可运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

现有测试涉及文档解析、切分、模型懒加载和基础接口；本次本地运行 17 项通过。测试不覆盖真实数据库、模型下载与端到端问答。`eval_retrieval.py` 是依赖本地数据库的检索观察脚本，不包含完整标注集及自动化的 Recall/MRR 评分，因此本仓库目前没有可复现的整体准确率结论。

## 当前限制

- 扫描版或加密 PDF 暂不支持；DOCX 解析提取段落与表格文本，不保证还原所有排版。
- 当前应用没有用户登录、权限隔离或多租户功能。Compose 默认映射到主机的 8000 端口，不应在不可信网络或公网直接开放。
- 上传内容和问答会进入数据库，提问及检索到的上下文会发送给所配置的模型服务。使用真实资料前，请确认服务商的数据处理方式。
- 目前没有为知识库无答案情况提供可靠性保证，也没有提供大规模数据与并发性能结论。模型和网络错误需要结合日志排查。
