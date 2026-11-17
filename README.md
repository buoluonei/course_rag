# 课程资料 RAG 问答系统

在浏览器里上传课程资料，然后基于资料提问。项目使用 FastAPI、MySQL 和 DeepSeek API，支持文档管理、多轮问答、候选来源和问答历史。

本文介绍 **Windows + Docker Desktop 本地启动**。新用户只需在配置文件中填写自己的 **DeepSeek API Key**；网页运行在自己的电脑上，不是公开网站。

## 1. 准备

1. 安装并打开 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，等待 Docker 引擎启动。
2. 安装 Git；或者直接从 GitHub 下载 ZIP 并解压。
3. 准备 [DeepSeek API Key](https://platform.deepseek.com/)，并确认账户有可用额度。**DeepSeek 网页聊天账号与 API 额度是两回事。**
4. 连接网络。第一次构建需要下载 Python、MySQL、PyTorch CPU 版和其他依赖，可能需要几分钟或更久；普通问答还需要访问 DeepSeek 服务。

在 PowerShell 里检查软件：

```powershell
git --version
docker compose version
docker info
```

如果 `docker info` 提示无法连接，请先打开 Docker Desktop 并等待引擎启动。

## 2. 下载和配置

在 PowerShell 中选择项目存放位置。例如存放在桌面：

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/buoluonei/course_rag.git
cd course_rag
```

后续命令都在 `course_rag` 目录执行。下载 ZIP 的用户请进入解压后的目录。

复制配置模板并打开：

```powershell
Copy-Item .env.example .env
notepad .env
```

把唯一的占位项替换为自己的密钥并保存：

```text
DEEPSEEK_API_KEY=在此填写自己的DeepSeek API Key
```

应用固定使用 DeepSeek 官方 API 和 `deepseek-flash`，不用填写模型名、接口地址或数据库密码。`.env` 包含密钥，不要提交到 GitHub，也不要发给别人。

## 3. 启动并验证

确保 Docker Desktop 已经运行，在项目目录执行：

```powershell
docker compose up -d --build
```

首次构建需要下载依赖，请等待命令结束。检查容器：

```powershell
docker compose ps
```

正常情况下 `app` 和 `db` 都会运行。MySQL 第一次初始化需要一点时间；如果页面暂时报数据库错误，请等待几十秒再刷新。

打开 [http://127.0.0.1:8000/](http://127.0.0.1:8000/)。其他检查地址：

- [应用存活检查](http://127.0.0.1:8000/livez)：检查应用是否响应。
- [数据库连接检查](http://127.0.0.1:8000/readyz)：检查数据库连接，**不检查模型 API 或表结构**。
- [接口文档](http://127.0.0.1:8000/docs)：查看和调试接口。

应用日志：

```powershell
docker compose logs -f app
```

按 `Ctrl + C` 退出日志查看，不会停止服务。

## 4. 上传资料并提问

1. 在网页上传 TXT、可提取文字的 PDF 或 DOCX；TXT 使用 UTF-8 编码，单文件不超过 10 MiB。
2. 等待上传完成。可先上传项目内的 `data/course.txt`。
3. 提问：“什么是死锁？”
4. 查看回答和候选来源；可以追问、开始新对话或逐条删除历史。

“你好”等单独问候直接返回。默认使用 BM25 关键词检索，**不会在第一次提问时下载向量和重排序模型**。它启动门槛低，但对同义改写和跨段推理的能力有限；候选来源也不保证都被回答实际使用，请结合原文核对。扫描版或加密 PDF 和 Markdown 文件目前不能直接上传。

## 5. 停止和再次启动

在项目目录执行：

```powershell
docker compose down
```

普通停止保留 MySQL 数据卷。下次启动：

```powershell
docker compose up -d
```

修改代码后，使用 `docker compose up -d --build` 重建。**不要用 `docker compose down -v` 当作普通停止命令**，它会删除数据库卷及里面的资料和历史。

默认数据库密码只用于本机示例，数据库端口没有映射到宿主机，网页也仅绑定 `127.0.0.1`。本项目没有登录和用户隔离，不能直接开放到公网；数据卷也不能替代备份。

第一次运行会创建名为 `course-rag-v2_db_data` 的卷。如果这台电脑已经有同名卷，Compose 会复用已有数据；不要删除旧卷。如需并存，可在启动时指定一个新的项目名，例如：

```powershell
docker compose -p course-rag-mine up -d --build
```

之后停止或启动同一实例时，也要带上相同的 `-p course-rag-mine`。多个实例不能同时占用同一个 8000 端口。

## 6. 常见问题

**提示找不到 Docker 或不能连接 Docker**：启动 Docker Desktop，等待引擎启动；重新打开 PowerShell，执行 `docker info`。

**网页打不开 / 端口被占用**：先用 `docker compose ps` 和 `docker compose logs app` 检查。如果 8000 已被占用，可以在 `docker-compose.yml` 中把 `127.0.0.1:8000:8000` 改为 `127.0.0.1:8001:8000`，再执行 `docker compose up -d`，然后访问 `http://127.0.0.1:8001/`。

**数据库连接失败**：首次初始化时请稍等，查看 `docker compose logs db`。已有数据卷不会因修改 `db_init.sql` 而自动迁移，也不会因修改环境变量而自动更改原有数据库密码。不要直接删除数据卷，应先确认并备份其中的数据。

**提示 API Key 错误、额度不足或模型服务不可用**：检查 `.env` 的 DeepSeek 密钥、账户额度以及网络。修改 `.env` 后执行 `docker compose up -d` 使应用使用新配置。大模型调用可能收费。

**提示资料中没有答案**：默认关键词检索依赖文字匹配，换一种包含原文关键词的提问可能更容易命中。它并不等于对答案是否存在的可靠判断。

## 7. 检索原理与可选的混合检索

默认流程：

```text
上传 → 文档解析与切分 → MySQL 保存片段
提问 → BM25 关键词检索 → DeepSeek 回答 → 保存历史
```

代码同时保留 **BM25 + BGE 向量检索的 RRF 融合和 CrossEncoder 重排序**。这是可选的进阶模式，不是默认运行路径。要启用时，可在 `.env` 增加：

```text
COURSE_RETRIEVAL_MODE=hybrid
```

执行 `docker compose up -d` 后生效。首次有资料的问答会尝试下载 `BAAI/bge-small-zh-v1.5` 和 `BAAI/bge-reranker-base`，需要额外网络、磁盘空间和等待时间；当前 Compose 未单独持久化模型缓存，重建容器可能重新下载。混合检索不保证结果一定正确。恢复默认模式可删除这一行并重新运行 `docker compose up -d`。

## 8. 测试与目录

| 路径 | 内容 |
| --- | --- |
| `app/main.py`、`app/static/` | API、页面和交互 |
| `app/document_parser.py`、`app/chunking.py` | 文档解析与切分 |
| `app/vector_search.py` | BM25 与可选的混合检索、重排序 |
| `app/rag.py`、`app/database.py` | DeepSeek 调用与 MySQL 读写 |
| `db_init.sql`、`tests/` | 数据库初始化和单元测试 |

安装项目依赖后，可以在 Windows PowerShell 运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

本地单元测试不等于完整部署验证。本项目还没有可复现的大规模检索准确率和并发性能结论。上传资料和历史保存在数据库；问题及检索到的上下文会发送到 DeepSeek，使用真实资料前请考虑数据隐私。
