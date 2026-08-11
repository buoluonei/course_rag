from fastapi import FastAPI,File,UploadFile,HTTPException

from app.schemas.question import QuestionRequest
from app.database import save_question,list_questions,search_chunks,replace_chunks
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
def get_questions():
    rows=list_questions()
    questions=[]
    for row in rows:
        questions.append({"id":row[0],"question":row[1]})
    return {"questions":questions}

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
    keyword=question.replace("什么是", "").replace("？","")
    return answer_question(question,keyword)

@app.post("/documents/upload")
def upload_document(upload_file:UploadFile=File(...)):
    if not upload_file.filename.endswith(".txt"):
        raise HTTPException(status_code=400,detail="只支持TXT文件")
    content_bytes=upload_file.file.read()
    content=content_bytes.decode("utf-8")
    
    chunks=[]
    for line in content.split("\n"):
        if line!="":
            chunks.append(line)
    
    replace_chunks(chunks)
    return{"filename":upload_file.filename,"chunks_count":len(chunks)}            



