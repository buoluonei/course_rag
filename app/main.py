from fastapi import FastAPI

from app.schemas.question import QuestionRequest
from app.database import save_question,list_questions,search_chunks
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