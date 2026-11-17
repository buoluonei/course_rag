from fastapi import FastAPI,File,UploadFile,HTTPException
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.schemas.question import QuestionRequest
from app.database import (
    save_question,
    list_questions,
    search_chunks,
    get_question_by_id,
    delete_question,
    count_questions,
    list_documents,
    delete_document,
    find_document_by_filename,
    list_question_history,
    replace_document,
    DatabaseUnavailableError,
    get_connection
)
# 延迟导入这些模块，避免启动时加载模型卡住
# from app.rag import answer_question
# from app.vector_search import rebuild_embeddings,RetrievalModelUnavailableError,make_index_dirty
from app.document_parser import DocumentParseError,parse_document

from app.chunking import chunk_document


CHUNK_SIZE=200
CHUNK_OVERLAP=40

MAX_UPLOAD_SIZE=10*1024*1024

app = FastAPI(title="Course RAG Platform")

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")
    
@app.get("/livez")
def liveness():
    return {"status": "alive"}

@app.get("/readyz")
def readiness():
    connection=get_connection()
    cursor=None
    try:
        cursor=connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return {"status": "ready"}
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

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
    # 常见的单独问候无需加载检索模型；带有实际问题的输入仍走正常流程。
    greeting=request.question.strip().strip(" \t\r\n，。！？,.!?~～").lower()
    if greeting in {"你好", "您好", "嗨", "哈喽", "hello", "hi"}:
        result={"answer":"你好！你可以上传课程资料，然后向我提问。", "source":[], "source_count":0}
        save_question(request.question,result["answer"],request.session_id)
        return result

    # 延迟导入，避免启动时加载模型
    from app.rag import answer_question

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
    # 延迟导入
    from app.vector_search import make_index_dirty

    existing_id=find_document_by_filename(upload_file.filename)
    if existing_id is not None and not overwrite:
        raise HTTPException(status_code=409,detail="文件已存在,请使用overwrite参数覆盖")
    
    content_bytes=upload_file.file.read(MAX_UPLOAD_SIZE+1)
    
    if len(content_bytes)>MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413,detail="文件过大，最多支持10MB")
    
    try:
        blocks=parse_document(upload_file.filename,content_bytes)
    except DocumentParseError as error:
        raise HTTPException(status_code=400,detail=str(error)) from error
    
    chunk_objects=chunk_document(blocks,chunk_size=CHUNK_SIZE,chunk_overlap=CHUNK_OVERLAP)
    
    if not chunk_objects:
        raise HTTPException(status_code=400,detail="文件内容不能为空")
    
    try:
        document_id=replace_document(upload_file.filename,chunk_objects,existing_id=existing_id)
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        ) from error

    make_index_dirty()
    # 延迟构建向量：不在上传时立即构建，而是在查询时按需构建
    # rebuild_embeddings()  # 暂时注释掉，避免卡住
    return{"filename":upload_file.filename,"chunks_count":len(chunk_objects),"document_id":document_id}            

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
    # 延迟导入
    from app.vector_search import make_index_dirty

    deleted_count=delete_document(document_id)
    if deleted_count==0:
        raise HTTPException(status_code=404,detail="没有找到这条文档")
    make_index_dirty()
    # 延迟构建向量：不在删除时立即构建，而是在查询时按需构建
    # rebuild_embeddings()  # 暂时注释掉，避免卡住
    return {"message":"删除成功"}

@app.exception_handler(DatabaseUnavailableError)
async def database_error_handler(request,exc):
    return JSONResponse(status_code=503,content={"detail":"数据库暂不可用,请稍后再试"})

@app.exception_handler(Exception)
async def retrieval_model_error_handler(request,exc):
    # 延迟导入异常类
    from app.vector_search import RetrievalModelUnavailableError
    if isinstance(exc, RetrievalModelUnavailableError):
        return JSONResponse(status_code=503,content={"detail":"检索模型暂不可用,请稍后再试"})
    raise exc

@app.get("/sessions/{session_id}")
def get_session(session_id:str):
    rows=list_question_history(session_id)
    questions=[{"question":question,"answer":answer} for question,answer in rows]
    return {"session_id":session_id,"questions":questions}
