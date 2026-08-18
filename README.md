# 课程资料 RAG 问答系统

一个基于 FastAPI + MySQL + 大语言模型的多格式课程资料问答系统。上传资料后，系统会对资料分块保存，提问时检索相关资料片段，交给模型生成带来源引用的回答，并支持多轮对话与问答历史。

## 功能

- 上传 TXT 资料，按固定长度（100 字）加重叠（20 字）自动分块
- 同名文件覆盖策略：默认拒绝（409），前端确认后带 `overwrite=true` 强制覆盖
- 文档管理：查看文档列表、删除文档（连带删除资料块）
- RAG 问答：问题转成向量，与全部资料块做语义相似度匹配，取最相关的前 5 条作为上下文
- 多轮对话：通过 `session_id` 保存会话，历史问答作为上下文传给模型
- 回答附带来源：每条引用包含资料内容和文件名
- 问答历史：分页查看、单条查询、删除
- 网页界面 + Swagger 调试接口

## 技术栈

- 后端：FastAPI、Uvicorn
- 数据库：MySQL 8（`mysql-connector-python`）
- AI：OpenAI 兼容 API（通过 `openai` SDK 调用）
- 检索：向量语义检索（`sentence-transformers` + `bge-small-zh`）
- 配置：`python-dotenv`
- 前端：原生 HTML + JavaScript（`fetch`）

## 目录结构

```text
app/                 学习版主程序
  main.py            FastAPI 应用、网页、上传、问答、历史接口
  database.py        所有 MySQL 读写函数
  rag.py             关键词提取、检索、排序、模型调用
  schemas/question.py 请求数据模型
demo_app/            独立完整示例（多格式解析等，供参考）
data/                示例资料
tests/               基础测试
docs/                文档与计划
```

## 快速开始（Docker 推荐）

需要先安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

1. 克隆仓库并进入目录（推荐用 `git clone`，比下载 ZIP 省事，也不会出现解压套娃）：

```powershell
git clone https://github.com/buoluonei/course_rag.git
cd course_rag
```

> 注意：后续所有命令都要在**包含 `docker-compose.yml` 的项目根目录**里执行。

2. 复制配置模板并填写：

```powershell
Copy-Item .env.example .env
```

打开 `.env` 填写四个配置项：

- `COURSE_DB_PASSWORD`：**随便填**，Docker 会用这个密码自动创建 MySQL，应用也用同一个密码连接，不需要提前安装 MySQL
- `COURSE_LLM_BASE_URL` / `COURSE_LLM_MODEL` / `COURSE_LLM_API_KEY`：填**你自己的**模型接口信息（没有 API Key 也能启动系统、上传资料，但提问不会回答）

3. 启动：

```powershell
docker compose up -d --build
```

4. 打开 <http://localhost:8000/> 即可使用

> 提示：MySQL 首次启动需要初始化（自动建库建表），如果页面暂时提示数据库错误，等十几秒再刷新。

## 环境准备

1. 安装依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. 复制配置模板并填写：

```text
将 .env.example 复制为 .env，然后填入自己的 MySQL 密码和模型 API 信息
```

`.env` 已被 `.gitignore` 忽略，不会提交到 GitHub。

3. 初始化数据库（需要 MySQL 已启动）：

```powershell
mysql -u root -p < db_init.sql
```

脚本会创建 `course_rag` 数据库和三张表：`documents`、`chunks`、`questions`。

## 启动

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- 网页：http://127.0.0.1:8000/
- Swagger：http://127.0.0.1:8000/docs

## 主要接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /health | 健康检查 |
| POST | /documents/upload?overwrite=true/false | 上传 TXT，同名默认 409 |
| GET | /documents | 文档列表 |
| DELETE | /documents/{id} | 删除文档及其资料块 |
| POST | /answers | 提问（可带 session_id 实现多轮） |
| GET | /questions?limit=&offset= | 问答历史分页 |
| GET | /questions/{id} | 单条问答 |
| DELETE | /questions/{id} | 删除问答 |
| GET | /search?keyword= | 搜索资料片段 |

## 关键实现

- **分块**：`split_chunks` 按固定长度切块，前后块保留重叠，避免边界信息丢失
- **中文关键词**：先删除停用词（什么、为什么、如何等），再生成两字组合作为搜索词
- **检索排序**：中文嵌入模型把资料块转成向量，提问时用余弦相似度匹配，取前 5
- **同名覆盖**：先查同名文档，冲突返回 409；确认覆盖后才在内容校验通过后删除旧文档
- **多轮对话**：按 `session_id` 读取历史问答，组装成 `user/assistant` 消息再调用模型
- **安全**：所有 SQL 使用参数化查询；网页渲染来源时用 `textContent` 而非拼接 HTML

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- `tests/test_health.py`：健康检查接口测试
- `tests/test_question_schema.py`：提问请求参数校验测试
