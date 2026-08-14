from fastapi import FastAPI,File,UploadFile,HTTPException

from app.schemas.question import QuestionRequest
from app.database import save_question,list_questions,search_chunks,replace_chunks,get_question_by_id,delete_question,count_questions,save_document,list_documents,delete_document
from app.rag import answer_question


app = FastAPI(title="Course RAG Platform")

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

def search_questions(keyword:str):
    rows=search_chunks(keyword)
    results=[]
    for row in rows:
        results.append({"id":row[0],"question":row[1]})
    return {"results":results}

@app.post("/answers")
def answer(request:QuestionRequest):
    question=request.question
    result=answer_question(question)
    save_question(question,result["answer"])
    return result

@app.post("/documents/upload")
def upload_document(upload_file:UploadFile=File(...)):
    if not upload_file.filename.endswith(".txt"):
        raise HTTPException(status_code=400,detail="只支持TXT文件")
    content_bytes=upload_file.file.read()
    try:
        content=content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400,detail="文件必须使用UTF-8编码")
    
    chunks=[]
    for line in content.split("\n"):
        line=line.strip()
        if line!="":
            chunks.append(line)
    if len(chunks)==0:
        raise HTTPException(status_code=400,detail="文件内容不能为空")
    document_id=save_document(upload_file.filename)
    replace_chunks(chunks,document_id)
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
    return {"message":"删除成功"}
