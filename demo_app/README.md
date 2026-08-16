# Course RAG Demo

这是一个独立于练习代码的可运行演示版。它使用 `demo_chunks` 和 `demo_questions` 两张表，不会清空你当前练习版使用的 `chunks` 与 `questions`。

## 启动前配置

项目根目录的 `.env` 需要包含：

```text
COURSE_DB_PASSWORD=你的 MySQL 密码
COURSE_LLM_BASE_URL=https://apiclaude.cc/v1
COURSE_LLM_MODEL=gpt-5.6-terra
COURSE_LLM_API_KEY=你的 API 密钥
```

如果尚未安装依赖，在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 启动

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn demo_app.main:app --reload
```

浏览器打开 `http://127.0.0.1:8000/` 查看网页，或打开 `http://127.0.0.1:8000/docs` 使用 Swagger。

## 演示顺序

1. 调用 `POST /documents/upload`，上传 TXT、PDF 或 DOCX 资料。
2. 调用 `POST /answers`，提交：

```json
{"question": "多个进程互相等待资源是什么情况？"}
```

3. 调用 `GET /questions` 查看历史问答。
4. 调用 `GET /questions/{question_id}` 或 `DELETE /questions/{question_id}` 操作单条记录。

## 当前范围

- 支持 UTF-8 TXT、文字版 PDF 和 DOCX；新文件会覆盖 Demo 中的旧资料。
- DOCX 会提取正文段落和表格文字。
- 扫描版或加密 PDF 暂不支持，接口会返回明确的错误信息。
- 资料按固定长度切片并保留少量重叠；提问时按关键词给片段排序，每次使用最相关的 8 个片段。
- 回答会保存问题、答案和创建时间，并返回引用资料。
- 当前使用轻量关键词检索，适合演示和中小型课程资料；后续可替换为向量检索。
- 如果资料中没有任何相关关键词，系统不会把无关片段交给模型，而是直接返回“资料中没有答案”。
