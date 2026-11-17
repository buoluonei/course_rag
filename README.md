# 课程资料 RAG 问答系统

上传课程资料，在浏览器里提问，系统会查找相关片段并结合大模型生成回答。支持 TXT、PDF、DOCX，提供问答历史和文档管理。

本文优先介绍 **Windows + Docker Desktop 本地部署**：完成后，你可以在自己的电脑上通过浏览器使用。项目代码放在 GitHub 上，并不代表已有可供访问的在线服务。

## 一、开始之前

### 1. 准备软件

- **Docker Desktop**：用于运行应用和 MySQL。安装并打开后，等待 Docker 引擎启动。
- **Git**：用于从 GitHub 下载项目。如果下载的是 ZIP，可以解压后跳过 `git clone`，直接进入解压后的项目目录。
- **浏览器**：例如 Edge、Chrome。
- **模型 API**：需要一个支持 OpenAI 兼容 Chat Completions 接口的服务，准备好接口地址、模型名称和 API Key。服务可能收费，以服务商说明为准。

在 PowerShell 中检查软件是否可用：

```powershell
git --version
docker --version
docker compose version
docker info
```

前三条应显示版本信息；最后一条应能显示 Docker 信息。如果提示无法连接 Docker，请先打开 Docker Desktop，等引擎启动后重试。

> 首次构建需要下载 Python、MySQL 镜像及项目依赖。首次问答还可能下载两个检索模型，需要网络连接和一定等待时间。

### 2. 下载项目

打开 PowerShell，先进入自己想存放项目的文件夹，例如桌面：

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/buoluonei/course_rag.git
cd course_rag
```

后续命令都在 `course_rag` 项目根目录执行。可以用下面的命令确认目录中有 `docker-compose.yml`：

```powershell
Get-ChildItem docker-compose.yml
```

## 二、填写配置

### 1. 创建并打开配置文件

首次使用时，在项目根目录运行：

```powershell
Copy-Item .env.example .env
notepad .env
```

记事本会打开 `.env`。把模板中的占位内容替换成自己的配置，保存并关闭。

### 2. 各项配置的含义

```text
COURSE_DB_PASSWORD=在这里设置数据库密码
COURSE_LLM_BASE_URL=在这里填写模型服务接口地址
COURSE_LLM_MODEL=在这里填写模型名称
COURSE_LLM_API_KEY=在这里填写API密钥
COURSE_DB_HOST=localhost
HF_ENDPOINT=https://hf-mirror.com
```

| 配置项 | 要填写什么 |
| --- | --- |
| `COURSE_DB_PASSWORD` | 自己为项目数据库设置的密码。首次运行时，MySQL 和应用使用同一个值。 |
| `COURSE_LLM_BASE_URL` | 模型服务商提供的 OpenAI 兼容接口地址。是否带 `/v1` 等前缀，以服务商说明为准。 |
| `COURSE_LLM_MODEL` | 模型服务商提供的模型名称。 |
| `COURSE_LLM_API_KEY` | 模型服务商提供的 API Key，真实问答需要有效的密钥和可用额度。 |
| `COURSE_DB_HOST` | Docker 启动时会由 Compose 自动设置为 `db`，保留模板值即可。 |
| `HF_ENDPOINT` | 检索模型下载地址；模板提供了镜像地址，可根据网络环境调整。 |

**数据库密码和 API Key 是两回事**：前者连接本项目的 MySQL，后者调用外部大模型。`.env` 含有私密信息，不要提交到 GitHub 或发给别人。

MySQL 数据卷首次初始化后，修改 `.env` 中的数据库密码不会自动修改已有 MySQL 用户密码；请妥善记录，避免随意更改。

## 三、启动并检查

### 1. 构建并启动

仍在项目根目录执行：

```powershell
docker compose up -d --build
```

第一次运行会下载镜像和安装依赖，可能需要较长时间。命令结束后查看容器：

```powershell
docker compose ps
```

正常情况下应能看到 `app` 和 `db` 服务处于运行状态。MySQL 首次初始化还需要一些时间；服务刚启动后访问失败，可以稍等片刻再试。

### 2. 检查服务

在浏览器分别访问：

- [项目页面](http://127.0.0.1:8000/)
- [进程检查 /livez](http://127.0.0.1:8000/livez)：检查应用进程是否响应。
- [数据库连接检查 /readyz](http://127.0.0.1:8000/readyz)：检查应用能否连接数据库。
- [接口文档 /docs](http://127.0.0.1:8000/docs)：查看和调试接口。

能打开页面或通过 `/livez`，不代表数据库和模型 API 一定可用；`/readyz` 检查数据库连接，不检查表结构或模型 API。完成下一节的问答才能进一步检查实际使用流程。

查看日志可运行：

```powershell
docker compose logs -f app
```

数据库问题可以查看：

```powershell
docker compose logs -f db
```

按 `Ctrl + C` 只退出日志查看，不会停止服务。

## 四、第一次使用

1. 打开 [http://127.0.0.1:8000/](http://127.0.0.1:8000/)。
2. 上传一份 TXT、可提取文字的 PDF 或 DOCX 文档；TXT 必须是 UTF-8 编码，单个文件不超过 10 MiB。
3. 等待上传处理完成，在页面中输入与文档有关的问题并发送。
4. 查看回答及候选来源，可以继续追问，或使用页面上的新对话功能。

例如，可以上传项目中的 `data/course.txt`，提问：**“什么是死锁？”**

首次有资料的问答需要加载 `BAAI/bge-small-zh-v1.5` 向量模型和 `BAAI/bge-reranker-base` 重排序模型；模型尚未缓存时会尝试下载。下载失败时请检查网络和 `HF_ENDPOINT` 配置。

页面返回的来源是提供给模型的**候选片段**，不保证每个片段都被回答实际采用，回答也可能出错，请结合原文核对。扫描版或加密 PDF 暂不支持，`.md` 文件目前不支持直接上传。

## 五、停止与再次启动

在项目根目录停止服务：

```powershell
docker compose down
```

再次启动：

```powershell
docker compose up -d
```

修改项目代码或前端后，需要重新构建镜像：

```powershell
docker compose up -d --build
```

普通 `down` 会保留 MySQL 数据卷，文档和问答记录保存在其中。`docker compose down -v` 会删除 Compose 命名卷及其中的数据库数据，请勿把它当作普通停止命令。

当前 Compose 没有为模型缓存单独配置数据卷；容器重建后可能需要再次下载模型。数据库数据卷也不能替代独立备份，请根据实际使用情况备份重要资料。

## 六、常见问题

### 运行命令提示找不到 Docker 或无法连接 Docker

确认已安装并打开 Docker Desktop，等待引擎启动；重新打开 PowerShell 后执行 `docker info` 检查。

### 浏览器打不开 8000 端口

先执行 `docker compose ps` 和 `docker compose logs app` 查看应用是否启动。如果提示端口已被占用，可在 `docker-compose.yml` 的 `app.ports` 中将 `8000:8000` 改成 `8001:8000`，然后执行 `docker compose up -d`，访问 `http://127.0.0.1:8001/`。左边是电脑端口，右边是容器端口。

### 数据库连接失败

首次启动请稍等 MySQL 初始化。检查 `docker compose ps`、`docker compose logs db`，确认 `.env` 中的数据库密码与已有数据库一致。已有数据卷不会因修改 `db_init.sql` 而自动迁移；也不要为排错随意删除数据卷。

### 提问时卡住或报模型错误

首次问答可能正在下载或加载检索模型，请查看应用日志。若下载失败，检查网络和模型下载地址；若模型 API 调用失败，检查服务商接口地址、模型名、API Key 和可用额度。修改 `.env` 后可执行 `docker compose up -d` 让配置生效，再查看日志。

## 七、工作原理

```text
上传文件 → 解析与切分 → MySQL 保存资料片段
提问 → BM25 + 向量检索 → RRF 融合 → 重排序 → 模型回答 → 保存问答
```

- 上传后按文档结构处理正文，较长内容使用最多 200 字、重叠 40 字的窗口切分。
- 检索时融合关键词排名和语义排名，最多选取 20 个候选片段；CrossEncoder 重排序后最多取 5 个作为上下文。
- 使用 OpenAI 兼容模型接口生成回答，按会话 ID 关联历史问答。
- 向量缓存与当前片段 ID 不一致时，会在查询时重新编码；该回退过程目前不会自动写回缓存，重复查询可能较慢。

## 八、项目结构与开发

```text
app/main.py             页面与 API 路由
app/static/             页面、样式和交互脚本
app/document_parser.py  TXT、PDF、DOCX 解析
app/chunking.py         文档切分
app/vector_search.py    混合检索与重排序
app/rag.py              模型调用与上下文组装
app/database.py         MySQL 读写
db_init.sql             数据库初始化
tests/                  单元测试
```

不用 Docker 开发时，需要自行准备 Python 3.11 和 MySQL 8，执行 `db_init.sql`，并在 `.env` 中配置本地数据库地址及其 root 密码：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

运行单元测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

测试覆盖文档解析、切分、模型懒加载和基础接口，不代表真实数据库、模型下载及端到端问答已经验证。`eval_retrieval.py` 是依赖本地数据库的检索观察脚本，目前没有可复现的整体准确率结论。

## 当前限制

- 项目没有用户登录、权限隔离或多租户功能，默认端口映射可能被其他设备访问；不要直接部署到公网。
- 上传内容和问答保存在数据库中；问题与检索上下文会发送给所配置的模型服务。使用真实资料前请确认数据处理方式。
- 目前不保证资料不足时总能正确拒答，也没有大规模数据和并发性能结论。
- 上述 Docker 步骤基于仓库配置编写；尚未在全新机器上完整验证从下载到真实模型问答的全部流程。

