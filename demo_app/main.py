from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from demo_app.database import (
    count_chunks,
    count_questions,
    delete_question,
    ensure_tables,
    get_question_by_id,
    list_questions,
    replace_chunks,
    save_question,
)
from demo_app.document_parser import DocumentParseError, parse_document
from demo_app.rag import ModelServiceUnavailableError, answer_question


app = FastAPI(title="Course RAG Demo", version="1.0.0")
ensure_tables()


PAGE = """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>课程资料问答 Demo</title>
<style>
body{font-family:system-ui, sans-serif;max-width:900px;margin:40px auto;padding:0 20px;background:#f5f7fb;color:#172033}
main{background:white;padding:28px;border-radius:16px;box-shadow:0 8px 30px #17203318}h1{margin-top:0}
section{border-top:1px solid #e6e9ef;padding-top:20px;margin-top:24px}input,button{font:inherit;padding:10px;border:1px solid #ccd3df;border-radius:8px}button{background:#2563eb;color:white;border:0;cursor:pointer;margin-left:8px}.question{width:70%}
#answer{white-space:pre-wrap;line-height:1.7}.source{background:#f5f7fb;padding:10px;border-radius:8px;margin:8px 0;font-size:.95rem}.history{padding:12px 0;border-bottom:1px solid #edf0f5}
.muted{color:#64748b}
</style></head>
<body><main><h1>课程资料问答</h1><p class="muted">先上传 TXT、PDF 或 DOCX 资料，再输入问题。扫描版 PDF 暂不支持。</p>
<section><h2>1. 上传资料</h2><input id="file" type="file" accept=".txt,.pdf,.docx"><button onclick="upload()">上传并替换</button><p id="uploadStatus"></p></section>
<section><h2>2. 提问</h2><input id="question" class="question" placeholder="例如：鱼油为什么需要避光保存？"><button onclick="ask()">提交问题</button><p id="answer"></p><div id="sources"></div></section>
<section><h2>历史问答</h2><button onclick="loadHistory()">刷新历史</button><div id="history"></div></section></main>
<script>
async function upload(){const file=document.getElementById('file').files[0];if(!file){alert('请先选择 TXT 文件');return;}const data=new FormData();data.append('uploaded_file',file);const r=await fetch('/documents/upload',{method:'POST',body:data});const j=await r.json();document.getElementById('uploadStatus').textContent=r.ok?`已上传 ${j.filename}，生成 ${j.chunks_count} 个资料片段`:j.detail;}
function addTextCard(parent,className,title,content){const card=document.createElement('div');card.className=className;const heading=document.createElement('b');heading.textContent=title;card.append(heading,document.createElement('br'),document.createTextNode(content));parent.appendChild(card);}
async function ask(){const question=document.getElementById('question').value;const r=await fetch('/answers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});const j=await r.json();document.getElementById('answer').textContent=r.ok?j.answer:j.detail;const sources=document.getElementById('sources');sources.replaceChildren();if(r.ok){j.sources.forEach(s=>addTextCard(sources,'source',`片段 ${s.id}`,s.content));loadHistory();}}
async function loadHistory(){const r=await fetch('/questions?limit=10');const j=await r.json();const history=document.getElementById('history');history.replaceChildren();if(!(j.questions||[]).length){const empty=document.createElement('p');empty.className='muted';empty.textContent='暂无记录';history.appendChild(empty);return;}j.questions.forEach(x=>addTextCard(history,'history',x.question,x.answer));}
loadHistory();
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents/status")
def document_status():
    return {"chunk_count": count_chunks()}


@app.post("/documents/upload")
async def upload_document(uploaded_file: UploadFile = File(...)):
    filename = uploaded_file.filename or ""
    content_bytes = await uploaded_file.read()
    await uploaded_file.close()

    try:
        content = parse_document(filename, content_bytes)
    except DocumentParseError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    chunks = []
    chunk_size = 700
    overlap = 100
    start = 0
    while start < len(content):
        chunk = content[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    if not chunks:
        raise HTTPException(status_code=400, detail="文件内容不能为空")

    replace_chunks(chunks)
    return {"filename": filename, "chunks_count": len(chunks)}


@app.post("/answers")
def create_answer(request: QuestionRequest):
    try:
        result = answer_question(request.question)
    except ModelServiceUnavailableError as error:
        raise HTTPException(
            status_code=503,
            detail="模型服务暂时不可用，请稍后再试",
        ) from error

    if result is None:
        raise HTTPException(status_code=409, detail="请先上传课程资料")

    save_question(request.question, result["answer"])
    return result


@app.get("/questions")
def get_questions(limit: int = 20, offset: int = 0):
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(
            status_code=400,
            detail="limit 必须在 1 到 100 之间，offset 不能小于 0",
        )

    rows = list_questions(limit, offset)
    questions = []
    for row in rows:
        questions.append(
            {
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "created_at": row[3],
            }
        )

    return {
        "questions": questions,
        "total": count_questions(),
        "limit": limit,
        "offset": offset,
    }


@app.get("/questions/{question_id}")
def get_question(question_id: int):
    row = get_question_by_id(question_id)
    if row is None:
        raise HTTPException(status_code=404, detail="没有找到这条问答记录")

    return {
        "id": row[0],
        "question": row[1],
        "answer": row[2],
        "created_at": row[3],
    }


@app.delete("/questions/{question_id}")
def remove_question(question_id: int):
    if delete_question(question_id) == 0:
        raise HTTPException(status_code=404, detail="没有找到这条问答记录")

    return {"message": "删除成功"}
