import os

from dotenv import load_dotenv
from openai import OpenAI,APIError
from fastapi import HTTPException
from app.vector_search import rerank

load_dotenv()

client=OpenAI(
    api_key=os.getenv("COURSE_LLM_API_KEY"),
    base_url=os.getenv("COURSE_LLM_BASE_URL")
)

def extract_keywords(question):
    words=["为什么","是","如何","什么","?","怎么"]
    for word in words:
        question=question.replace(word,"")
    text=[]
    for i in range(len(question)-1):
        text.append(question[i:i+2])
    return text

def make_bigrams(text):
    result=[]
    for i in range(len(text)-1):
        result.append(text[i:i+2])
    return result

def answer_question(question,history=None):
    top=rerank(question)
    if not top:
        return{"answer":"资料中没有答案","source":[],"source_count":0}
    
    parts=[]
    source=[]
    for row,score in top:
        parts.append(row[1])
        source.append({"id":row[0],"content":row[1],"filename":row[2],"score":score})
    context="\n".join(parts)
    
    prompt=(
    "你是课程资料的问答助手,请只根据以下资料回答问题。\n"
    "如果资料中没有答案，请明确说不知道\n"
    "资料：\n"
    +context
    +"\n问题:\n"
    +question
    )
    
    messages=[]
    if history:
        for question_text,answer_text in history:
            messages.append({"role":"user","content":question_text})
            messages.append({"role":"assistant","content":answer_text})
    messages.append({"role":"user","content":prompt})
    
    try:
        response=client.chat.completions.create(
            model=os.getenv("COURSE_LLM_MODEL"),
            messages=messages
        )
    except APIError:
       raise HTTPException(status_code=503,detail="模型服务暂不可用，请稍后再试")
    answer=response.choices[0].message.content
    return{"answer":answer,"source":source,"source_count":len(source)}