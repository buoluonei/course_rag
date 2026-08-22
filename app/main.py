from fastapi import FastAPI,File,UploadFile,HTTPException
from fastapi.responses import HTMLResponse

from app.schemas.question import QuestionRequest
from app.database import save_question,list_questions,search_chunks,replace_chunks,get_question_by_id,delete_question,count_questions,save_document,list_documents,delete_document,find_document_by_filename,list_question_history
from app.rag import answer_question
from app.vector_search import rebuild_embeddings

app = FastAPI(title="Course RAG Platform")

PAGE = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>课程问答</title></head>
<body>
<h1>课程资料问答</h1>
<section>
<h2>1. 上传资料</h2>
<input id="file" type="file" accept=".txt">
<button onclick="upload()">上传</button>
<p id="uploadStatus"></p>
</section>
<section>
<h2>2. 提问</h2>
<input id="question" placeholder="请输入问题">
<button onclick="ask()">提问</button>
<button onclick="newConversation()">新对话</button>
<span id="searchStatus" style="display:none">检索中…</span>
<p id="result"></p>
<div id="sources"></div>
</section>
<section>
<h2>3. 历史问答</h2>
<button onclick="loadHistory()">刷新历史</button>
<div id="history"></div>
</section>
<script>
let sessionId=crypto.randomUUID();

async function upload(){
    const fileInput=document.getElementById("file");
    if(!fileInput.files[0]){
        alert("请先选择 TXT 文件");
        return;
    }
    const form=new FormData();
    form.append("upload_file",fileInput.files[0]);
    let response=await fetch("/documents/upload",{method:"POST",body:form});
    let data=await response.json();
    if(response.status===409){
        if(confirm("同名文件已存在，是否覆盖？")){
            response=await fetch("/documents/upload?overwrite=true",{method:"POST",body:form});
            data=await response.json();
        }else{
            return;
        }
    }
    document.getElementById("uploadStatus").textContent=response.ok
        ? "上传成功："+data.filename+"，"+data.chunks_count+" 个片段"
        : data.detail;
}

async function ask(){
    const question=document.getElementById("question").value;
    if(!question){
        return;
    }
    const statusBox=document.getElementById("searchStatus");
    statusBox.style.display="inline";
    try{
        const response=await fetch("/answers",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({"question":question,"session_id":sessionId})
        });
        const data=await response.json();
        document.getElementById("result").textContent=response.ok
            ? data.answer
            : data.detail;

        const sourceBox=document.getElementById("sources");
        sourceBox.replaceChildren();
        if(data.source){
            const title=document.createElement("p");
            title.textContent="引用的资料（共 "+data.source.length+" 条）：";
            sourceBox.appendChild(title);
            data.source.forEach(function(s){
                const p=document.createElement("p");
                const scoreText=typeof s.score==="number" ? " 相关度 "+s.score.toFixed(3) : "";
                p.textContent="【"+s.filename+"】"+scoreText+"："+s.content;
                sourceBox.appendChild(p);
            });
        }
        loadHistory();
    }catch(error){
        document.getElementById("result").textContent="请求失败："+error;
    }finally{
        statusBox.style.display="none";
    }
}

async function loadHistory(){
    const response=await fetch("/questions?limit=10");
    const data=await response.json();
    const box=document.getElementById("history");
    box.replaceChildren();
    data.questions.forEach(function(q){
        const p=document.createElement("p");
        p.textContent="问："+q.question+"\\n答："+q.answer;
        box.appendChild(p);
    });
}

function newConversation(){
    sessionId=crypto.randomUUID();
    document.getElementById("result").textContent="";
    document.getElementById("sources").replaceChildren();
}
</script>
</body>
</html>
"""

@app.get("/",response_class=HTMLResponse)
def home():
    return PAGE

def split_chunks(text,chunk_size=100,overlap=20):
    chunks=[]
    start=0
    while start<len(text)-chunk_size:
        chunk=text[start:start+chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start+=chunk_size-overlap
    if start<len(text):
        tail=text[start:].strip()
        if tail:
            chunks.append(tail)
    return chunks
    
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/questions/preview")
def preview_question(request:QuestionRequest):
    question=request.question
    return {"question":question}

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
    if not upload_file.filename.endswith(".txt"):
        raise HTTPException(status_code=400,detail="只支持TXT文件")
    
    existing_id=find_document_by_filename(upload_file.filename)
    if existing_id is not None and not overwrite:
        raise HTTPException(status_code=409,detail="文件已存在,请使用overwrite参数覆盖")
    
    content_bytes=upload_file.file.read()
    try:
        content=content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400,detail="文件必须使用UTF-8编码")
    
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
