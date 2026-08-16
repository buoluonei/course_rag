# 课程资料 RAG 问答系统

一个基于 FastAPI + MySQL + 大语言模型的多格式课程资料问答系统。上传资料后，系统会对资料分块保存，提问时检索相关资料片段，交给模型生成带来源引用的回答，并支持多轮对话与问答历史。

## 功能

- 上传 TXT 资料，按固定长度（100 字）加重叠（20 字）自动分块
- 同名文件覆盖策略：默认拒绝（409），前端确认后带 `overwrite=true` 强制覆盖
- 文档管理：查看文档列表、删除文档（连带删除资料块）
- RAG 问答：问题先提取关键词，检索相关片段，按命中次数排序后取前 5 条作为上下文
- 多轮对话：通过 `session_id` 保存会话，历史问答作为上下文传给模型
- 回答附带来源：每条引用包含资料内容和文件名
- 问答历史：分页查看、单条查询、删除
- 网页界面 + Swagger 调试接口

## 技术栈

- 后端：FastAPI、Uvicorn
- 数据库：MySQL 8（`mysql-connector-python`）
- AI：OpenAI 兼容 API（通过 `openai` SDK 调用）
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

1. 克隆仓库并进入目录
2. 复制 `.env.example` 为 `.env`，填入自己的 MySQL 密码和模型 API 信息
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
- **检索排序**：统计每个资料块命中关键词的次数，按分数从高到低取前 5
- **同名覆盖**：先查同名文档，冲突返回 409；确认覆盖后才在内容校验通过后删除旧文档
- **多轮对话**：按 `session_id` 读取历史问答，组装成 `user/assistant` 消息再调用模型
- **安全**：所有 SQL 使用参数化查询；网页渲染来源时用 `textContent` 而非拼接 HTML

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- `tests/test_health.py`：健康检查接口测试
- `tests/test_question_schema.py`：提问请求参数校验测试
