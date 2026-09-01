from fastapi import FastAPI,File,UploadFile,HTTPException
from fastapi.responses import HTMLResponse,JSONResponse

from app.schemas.question import QuestionRequest
from app.database import save_question,list_questions,search_chunks,replace_chunks,get_question_by_id,delete_question,count_questions,save_document,list_documents,delete_document,find_document_by_filename,list_question_history,DatabaseUnavailableError
from app.rag import answer_question
from app.vector_search import rebuild_embeddings,RetrievalModelUnavailableError
from app.document_parser import DocumentParseError,parse_document

CHUNK_SIZE=200
CHUNK_OVERLAP=40

MAX_UPLOAD_SIZE=100*1024*1024

app = FastAPI(title="Course RAG Platform")

PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>课程资料问答</title>
<style>
:root{
  --ink:#111827;
  --muted:#64748b;
  --line:#e2e8f0;
  --line-strong:#cbd5e1;
  --paper:#ffffff;
  --canvas:#f4f6fa;
  --blue:#2563eb;
  --blue-dark:#1d4ed8;
  --blue-soft:#eff6ff;
  --green:#047857;
  --green-soft:#ecfdf5;
  --red:#b42318;
  --red-soft:#fff1f0;
  --shadow:0 1px 2px rgba(15,23,42,.04),0 8px 24px rgba(15,23,42,.06);
  --radius:10px;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--canvas);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}
button,input{font:inherit}
button{border:0;cursor:pointer}
svg{display:block;flex:0 0 auto}
.shell{width:min(1180px,calc(100% - 32px));margin:0 auto;padding:34px 0 60px}
.topbar{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:28px}
.eyebrow{margin:0 0 6px;color:var(--blue);font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
h1,h2,h3,p{margin-top:0}
h1{margin-bottom:6px;font-size:clamp(26px,4vw,38px);line-height:1.15;letter-spacing:0;font-weight:800}
h2{margin-bottom:4px;font-size:18px;line-height:1.3;font-weight:700}
.subtitle{margin:0;color:var(--muted);max-width:640px;font-size:14px}
.session-badge{display:inline-flex;align-items:center;gap:8px;padding:7px 12px;border:1px solid var(--line);border-radius:999px;background:var(--paper);color:var(--muted);font-size:12px;white-space:nowrap;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.session-dot{width:7px;height:7px;border-radius:50%;background:#10b981;box-shadow:0 0 0 3px rgba(16,185,129,.15)}
.layout{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(300px,.9fr);gap:22px;align-items:start}
.panel{border:1px solid var(--line);border-radius:var(--radius);background:var(--paper);box-shadow:var(--shadow)}
.panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:20px 22px 0}
.panel-body{padding:16px 22px 22px}
.panel-note{margin:0;color:var(--muted);font-size:13px}
.icon-badge{display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;background:var(--blue-soft);color:var(--blue);margin-bottom:10px}
.button{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:38px;padding:8px 14px;border-radius:8px;font-weight:600;font-size:14px;transition:background .15s,border-color .15s,transform .12s,box-shadow .15s;user-select:none}
.button:active{transform:translateY(1px)}
.button:disabled{cursor:not-allowed;opacity:.55;transform:none}
.button-primary{background:var(--blue);color:white;box-shadow:0 1px 2px rgba(37,99,235,.4)}
.button-primary:hover{background:var(--blue-dark)}
.button-quiet{border:1px solid var(--line);background:var(--paper);color:var(--ink)}
.button-quiet:hover{background:#f8fafc;border-color:var(--line-strong)}
.status{min-height:24px;margin:12px 0 0;font-size:13px;font-weight:500}
.status.success{color:var(--green)}
.status.error{color:var(--red)}
.question-box{display:flex;gap:10px}
.question-box input{width:100%;min-width:0;border:1px solid var(--line-strong);border-radius:8px;padding:11px 14px;outline:0;background:#fcfdfe;transition:border-color .15s,box-shadow .15s,background .15s}
.question-box input:focus{border-color:var(--blue);background:white;box-shadow:0 0 0 3px rgba(37,99,235,.12)}
.question-box input::placeholder{color:#94a3b8}
.question-actions{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:10px}
.hint{color:var(--muted);font-size:12px}
.top-actions{display:flex;align-items:center;gap:8px;margin-top:12px}
.answer-area{margin-top:22px;padding-top:20px;border-top:1px solid var(--line)}
.answer-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px}
.answer-label{font-size:13px;font-weight:700;color:var(--muted)}
.copy-button{display:inline-flex;align-items:center;gap:6px;min-height:30px;padding:4px 11px;border:1px solid var(--line);border-radius:7px;background:white;color:var(--ink);font-size:12px;font-weight:600;cursor:pointer;transition:border-color .15s,background .15s,color .15s}
.copy-button:hover{background:#f8fafc;border-color:var(--line-strong)}
.copy-button.copied{color:var(--green);border-color:var(--green);background:var(--green-soft)}
.answer-empty{color:var(--muted);font-size:14px;background:var(--canvas);border:1px dashed var(--line-strong);border-radius:8px;padding:18px 16px;margin:0}
.answer{white-space:pre-wrap;overflow-wrap:anywhere;font-size:16px;line-height:1.85;margin:0}
.sources{display:grid;gap:10px;margin-top:20px}
.source-card{padding:13px 15px;border:1px solid #dbeafe;border-left:3px solid #60a5fa;background:var(--blue-soft);border-radius:8px}
.source-meta{display:flex;justify-content:space-between;gap:10px;margin-bottom:6px;color:var(--muted);font-size:12px;font-weight:600}
.source-content{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;color:#334155}
.stack{display:grid;gap:22px}
.list{display:grid;gap:4px}
.list-empty{margin:0;color:var(--muted);font-size:13px;background:var(--canvas);border:1px dashed var(--line-strong);border-radius:8px;padding:14px 12px;text-align:center}
.upload-zone{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px;border:1px dashed var(--line-strong);border-radius:9px;background:#fbfcfe;transition:border-color .15s,background .15s}
.upload-zone:hover{border-color:var(--blue);background:var(--blue-soft)}
.upload-copy{min-width:0}
.upload-copy strong{display:block;margin-bottom:2px;font-size:14px}
.upload-copy span{display:block;color:var(--muted);font-size:12px;overflow-wrap:anywhere}
.file-control{display:flex;align-items:center;gap:10px;flex:0 0 auto}
.file-control input{max-width:220px;color:var(--muted);font-size:12px}
.file-control input::file-selector-button{margin-right:8px;padding:5px 10px;border:1px solid var(--line);border-radius:6px;background:white;color:var(--ink);font-size:12px;cursor:pointer}
.document-row,.history-row{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;padding:12px 8px;border-bottom:1px solid #eef2f7;border-radius:6px;transition:background .12s}
.document-row:hover,.history-row:hover{background:#f8fafc}
.document-row:last-child,.history-row:last-child{border-bottom:0}
.document-name{min-width:0;overflow-wrap:anywhere;font-weight:600;font-size:14px}
.document-date{color:var(--muted);font-size:12px;margin-top:2px}
.history-question{margin:0 0 4px;font-weight:650;overflow-wrap:anywhere;font-size:14px}
.history-answer{margin:0;color:var(--muted);font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}
.delete-button{flex:0 0 auto;padding:4px 8px;border-radius:6px;background:transparent;color:var(--red);font-size:12px;font-weight:600;transition:background .12s}
.delete-button:hover{background:var(--red-soft)}
.pagination{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:14px;padding-top:12px;border-top:1px solid #eef2f7}
.page-info{color:var(--muted);font-size:12px;white-space:nowrap}
.pagination .button{min-height:32px;padding:5px 10px;font-size:13px}
@media (max-width:820px){
  .shell{width:min(100% - 22px,620px);padding-top:22px}
  .topbar{display:block}
  .session-badge{margin-top:14px}
  .layout{grid-template-columns:1fr}
  .upload-zone,.question-box{align-items:stretch;flex-direction:column}
  .file-control{flex-direction:column;align-items:stretch}
  .file-control input{max-width:none}
  .question-actions{align-items:flex-start;flex-direction:column}
  .panel-head,.panel-body{padding-left:16px;padding-right:16px}
}
</style>
</head>
<body>
<main class="shell">
<header class="topbar">
<div><p class="eyebrow">COURSE RAG PLATFORM</p><h1>课程资料问答</h1><p class="subtitle">上传课程资料，基于资料内容提问，并查看回答依据。</p></div>
<div class="session-badge"><span class="session-dot"></span><span id="sessionLabel">当前对话已就绪</span></div>
</header>
<div class="layout">
<section class="panel">
<div class="panel-head"><div><span class="icon-badge"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></span><h2>提问工作区</h2><p class="panel-note">回答会附带检索到的原文片段。</p></div><button id="newConversationButton" class="button button-quiet" type="button"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12h14"/></svg>新对话</button></div>
<div class="panel-body">
<div class="question-box"><input id="question" type="text" maxlength="500" placeholder="例如：死锁的四个必要条件是什么？"><button id="askButton" class="button button-primary" type="button"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/></svg>提问</button></div>
<div class="question-actions"><span class="hint">Enter 提交</span></div>
<div class="top-actions"><button id="exportButton" class="button button-quiet" type="button"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/></svg>导出对话</button></div>
<div class="answer-area"><div class="answer-head"><span class="answer-label">回答</span><button id="copyAnswerButton" class="copy-button" type="button" hidden>复制回答</button></div><p id="answer" class="answer-empty">回答会显示在这里。</p><div id="sources" class="sources"></div></div>
</div>
</section>
<aside class="stack">
<section class="panel"><div class="panel-head"><div><span class="icon-badge"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg></span><h2>资料库</h2><p class="panel-note">支持 TXT、PDF、DOCX</p></div></div><div class="panel-body">
<div class="upload-zone"><div class="upload-copy"><strong>添加课程资料</strong><span>同名文件上传时会先请求确认</span></div><div class="file-control"><input id="file" type="file" accept=".txt,.pdf,.docx"><button id="uploadButton" class="button button-primary" type="button"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg>上传</button></div></div>
<p id="uploadStatus" class="status" aria-live="polite"></p><div id="documents" class="list"></div>
</div></section>
<section class="panel"><div class="panel-head"><div><span class="icon-badge"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8"/><path d="M8 13h5"/></svg></span><h2>问答历史</h2><p class="panel-note">分页查看全部记录</p></div><button id="refreshHistoryButton" class="button button-quiet" type="button"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>刷新</button></div><div class="panel-body"><div id="history" class="list"></div><div class="pagination"><button id="historyPrevButton" class="button button-quiet" type="button"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>上一页</button><span id="historyPageInfo" class="page-info">第 1 页</span><button id="historyNextButton" class="button button-quiet" type="button">下一页<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg></button></div></div></section>
</aside>
</div>
</main>
<script>
function newSessionId(){
    if(window.crypto&&typeof window.crypto.randomUUID==="function"){
        return window.crypto.randomUUID();
    }
    return "session-"+Date.now()+"-"+Math.random().toString(36).slice(2);
}
let sessionId=newSessionId();
let historyOffset=0;
const historyLimit=10;
const $=selector=>document.querySelector(selector);

function setStatus(element,message,type=""){
    element.textContent=message;
    element.className=`status ${type}`.trim();
}

async function readJson(response){
    const data=await response.json().catch(()=>({}));
    if(!response.ok){throw new Error(data.detail||`请求失败（${response.status}）`);}
    return data;
}

function addSource(source){
    const card=document.createElement("article");
    card.className="source-card";
    const meta=document.createElement("div");
    meta.className="source-meta";
    const fileName=document.createElement("span");
    fileName.textContent=source.filename||"未知文件";
    const score=document.createElement("span");
    score.textContent=typeof source.score==="number"?`相关度 ${source.score.toFixed(3)}`:"资料片段";
    meta.append(fileName,score);
    const content=document.createElement("p");
    content.className="source-content";
    content.textContent=source.content||"";
    card.append(meta,content);
    $("#sources").appendChild(card);
}

async function upload(){
    const file=$("#file").files[0];
    const status=$("#uploadStatus");
    if(!file){setStatus(status,"请先选择 TXT、PDF 或 DOCX 文件","error");return;}
    const form=new FormData();
    form.append("upload_file",file);
    $("#uploadButton").disabled=true;
    setStatus(status,"正在上传并建立索引…");
    try{
        let response=await fetch("/documents/upload",{method:"POST",body:form});
        if(response.status===409){
            if(!confirm("同名文件已存在，是否覆盖？")){setStatus(status,"已取消覆盖");return;}
            response=await fetch("/documents/upload?overwrite=true",{method:"POST",body:form});
        }
        const data=await readJson(response);
        setStatus(status,`已上传 ${data.filename}，生成 ${data.chunks_count} 个资料片段`,"success");
        $("#file").value="";
        await loadDocuments();
    }catch(error){setStatus(status,error.message,"error");}
    finally{$("#uploadButton").disabled=false;}
}

async function ask(){
    const input=$("#question");
    const question=input.value.trim();
    if(!question){input.focus();return;}
    const answer=$("#answer");
    $("#askButton").disabled=true;
    $("#newConversationButton").disabled=true;
    answer.className="answer-empty";
    answer.textContent="正在生成回答…";
    $("#sources").replaceChildren();
    try{
        const data=await readJson(await fetch("/answers",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question,session_id:sessionId})}));
        answer.className="answer";
        answer.textContent=data.answer||"模型没有返回回答。";
        $("#copyAnswerButton").hidden=false;
        resetCopyButton();
        (data.source||[]).forEach(addSource);
        historyOffset=0;
        await loadHistory();
    }catch(error){answer.className="answer-empty";answer.textContent=error.message;}
    finally{$("#askButton").disabled=false;$("#newConversationButton").disabled=false;}
}

async function exportConversation(){
    try{
        const data=await readJson(await fetch(`/sessions/${encodeURIComponent(sessionId)}`));
        const questions=data.questions||[];
        if(!questions.length){alert("当前会话还没有问答记录");return;}
        const lines=["# 课程问答对话记录",""];
        questions.forEach(function(item){
            lines.push(`## 问：${item.question}`,"");
            lines.push(item.answer||"","");
        });
        const blob=new Blob([lines.join("\\n")],{type:"text/markdown;charset=utf-8"});
        const url=URL.createObjectURL(blob);
        const link=document.createElement("a");
        link.href=url;
        link.download=`对话记录-${new Date().toISOString().slice(0,10)}.md`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }catch(error){
        alert(error.message);
    }
}

function resetCopyButton(){
    const button=$("#copyAnswerButton");
    button.classList.remove("copied");
    button.textContent="复制回答";
}

async function copyAnswer(){
    const button=$("#copyAnswerButton");
    const answer=$("#answer");
    if(!answer.textContent||answer.classList.contains("answer-empty")){return;}
    try{
        await navigator.clipboard.writeText(answer.textContent);
        button.classList.add("copied");
        button.textContent="已复制";
    }catch(error){
        button.textContent="复制失败";
    }
    setTimeout(resetCopyButton,1500);
}

function addDocument(documentInfo){
    const row=document.createElement("div");row.className="document-row";
    const info=document.createElement("div");
    const name=document.createElement("div");name.className="document-name";name.textContent=documentInfo.filename;
    const date=document.createElement("div");date.className="document-date";date.textContent=documentInfo.created_at?new Date(documentInfo.created_at).toLocaleString():"";
    info.append(name,date);
    const button=document.createElement("button");button.className="delete-button";button.type="button";button.textContent="删除";button.title=`删除 ${documentInfo.filename}`;
    button.addEventListener("click",()=>removeDocument(documentInfo.id,documentInfo.filename));
    row.append(info,button);$("#documents").appendChild(row);
}

async function loadDocuments(){
    const box=$("#documents");
    try{const data=await readJson(await fetch("/documents"));box.replaceChildren();if(!data.documents.length){const empty=document.createElement("p");empty.className="list-empty";empty.textContent="资料库还是空的。";box.appendChild(empty);return;}data.documents.forEach(addDocument);}
    catch(error){box.replaceChildren();const empty=document.createElement("p");empty.className="list-empty";empty.textContent=error.message;box.appendChild(empty);}
}

async function removeDocument(id,filename){
    if(!confirm(`确定删除“${filename}”吗？`)){return;}
    try{await readJson(await fetch(`/documents/${id}`,{method:"DELETE"}));await loadDocuments();}
    catch(error){setStatus($("#uploadStatus"),error.message,"error");}
}

function addHistory(item){
    const row=document.createElement("article");row.className="history-row";
    const question=document.createElement("p");question.className="history-question";question.textContent=item.question;
    const answer=document.createElement("p");answer.className="history-answer";answer.textContent=item.answer;
    row.append(question,answer);$("#history").appendChild(row);
}

async function loadHistory(){
    const box=$("#history");
    try{
        const data=await readJson(await fetch(`/questions?limit=${historyLimit}&offset=${historyOffset}`));
        box.replaceChildren();
        if(!data.questions.length){
            const empty=document.createElement("p");empty.className="list-empty";empty.textContent="还没有问答记录。";box.appendChild(empty);
        }else{
            data.questions.forEach(addHistory);
        }
        const total=data.total||0;
        const totalPages=Math.max(1,Math.ceil(total/historyLimit));
        const currentPage=Math.floor(historyOffset/historyLimit)+1;
        $("#historyPageInfo").textContent=`第 ${currentPage} / ${totalPages} 页，共 ${total} 条`;
        $("#historyPrevButton").disabled=historyOffset===0;
        $("#historyNextButton").disabled=historyOffset+historyLimit>=total;
    }
    catch(error){box.replaceChildren();const empty=document.createElement("p");empty.className="list-empty";empty.textContent=error.message;box.appendChild(empty);}
}

function newConversation(){
    sessionId=crypto.randomUUID();
    $("#sessionLabel").textContent="已开启新对话";
    $("#answer").className="answer-empty";
    $("#answer").textContent="回答会显示在这里。";
    $("#copyAnswerButton").hidden=true;
    resetCopyButton();
    $("#sources").replaceChildren();
    $("#question").focus();
}

$("#uploadButton").addEventListener("click",upload);
$("#askButton").addEventListener("click",ask);
$("#copyAnswerButton").addEventListener("click",copyAnswer);
$("#exportButton").addEventListener("click",exportConversation);
$("#newConversationButton").addEventListener("click",newConversation);
$("#refreshHistoryButton").addEventListener("click",loadHistory);
$("#historyPrevButton").addEventListener("click",()=>{historyOffset=Math.max(0,historyOffset-historyLimit);loadHistory();});
$("#historyNextButton").addEventListener("click",()=>{historyOffset+=historyLimit;loadHistory();});
$("#question").addEventListener("keydown",event=>{if(event.key==="Enter"){event.preventDefault();ask();}});
loadDocuments();loadHistory();
</script>
</body>
</html>
"""

@app.get("/",response_class=HTMLResponse)
def home():
    return PAGE

def split_chunks(text,chunk_size=CHUNK_SIZE,chunk_overlap=CHUNK_OVERLAP):
    chunks=[]
    start=0
    while start<len(text)-chunk_size:
        chunk=text[start:start+chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start+=chunk_size-chunk_overlap
    if start<len(text):
        tail=text[start:].strip()
        if tail:
            chunks.append(tail)
    return chunks
    
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/questions")
def get_questions(limit:int=10,offset:int=0):
    if limit<1 or limit>100 or offset<0:
        raise HTTPException(status_code=400,detail="limit必须在1到100之间,offset不能小于0")
    rows=list_questions(limit,offset)
    total=count_questions()
    
    questions=[]
    for row in rows:
        questions.append({"id":row[0],"question":row[1],"created_at":row[2],"answer":row[3]})
    return {"questions":questions,"total":total,"limit":limit,"offset":offset}

@app.get("/search")
def search_materials(keyword:str):
    rows=search_chunks(keyword)
    results=[]
    for row in rows:
        results.append({"id":row[0],"content":row[1],"filename":row[2]})
    return {"results":results}

@app.post("/answers")
def answer(request:QuestionRequest):
    question=request.question
    if request.session_id is None:
        history=[]
    else:
        history=list_question_history(request.session_id)
    result=answer_question(question,history)
    save_question(question,result["answer"],request.session_id)
    return result

@app.post("/documents/upload")
def upload_document(upload_file:UploadFile=File(...),overwrite:bool=False):
    existing_id=find_document_by_filename(upload_file.filename)
    if existing_id is not None and not overwrite:
        raise HTTPException(status_code=409,detail="文件已存在,请使用overwrite参数覆盖")
    
    content_bytes=upload_file.file.read()
    
    if upload_file.size is not None and upload_file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413,detail="文件过大，最多支持10MB")
    
    try:
        content=parse_document(upload_file.filename,content_bytes)
    except DocumentParseError as error:
        raise HTTPException(status_code=400,detail=str(error)) from error
    
    content=content.replace("\r\n","\n")
    chunks=split_chunks(content)
            
    if len(chunks)==0:
        raise HTTPException(status_code=400,detail="文件内容不能为空")
    
    if existing_id is not None:
        delete_document(existing_id)
        
    document_id=save_document(upload_file.filename)
    replace_chunks(chunks,document_id)
    rebuild_embeddings()
    return{"filename":upload_file.filename,"chunks_count":len(chunks),"document_id":document_id}            

@app.get("/questions/{question_id}")
def get_question(question_id:int):
    row=get_question_by_id(question_id)
    if row is None:
        raise HTTPException(status_code=404,detail="没有找到这条问答记录")
    return {"id":row[0],"question":row[1],"created_at":row[2],"answer":row[3]}

@app.delete("/questions/{question_id}")
def remove_question(question_id:int):
    deleted_count=delete_question(question_id)
    if deleted_count==0:
        raise HTTPException(status_code=404,detail="没有找到这条问答记录")
    return {"message":"删除成功"}

@app.get("/documents")
def get_documents():
    rows=list_documents()
    documents=[]
    for row in rows:
        documents.append({"id":row[0],"filename":row[1],"created_at":row[2]})
    return {"documents":documents}

@app.delete("/documents/{document_id}")
def remove_document(document_id:int):
    deleted_count=delete_document(document_id)
    if deleted_count==0:
        raise HTTPException(status_code=404,detail="没有找到这条文档")
    rebuild_embeddings()
    return {"message":"删除成功"}

@app.exception_handler(DatabaseUnavailableError)
async def database_error_handler(request,exc):
    return JSONResponse(status_code=503,content={"detail":"数据库暂不可用,请稍后再试"})

@app.exception_handler(RetrievalModelUnavailableError)
async def retrieval_model_error_handler(request,exc):
    return JSONResponse(status_code=503,content={"detail":"检索模型暂不可用,请稍后再试"})

@app.get("/sessions/{session_id}")
def get_session(session_id:str):
    rows=list_question_history(session_id)
    questions=[{"question":question,"answer":answer} for question,answer in rows]
    return {"session_id":session_id,"questions":questions}
