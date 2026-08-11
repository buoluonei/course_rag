import os

from dotenv import load_dotenv
from openai import OpenAI

from app.database import search_chunks

load_dotenv()

client=OpenAI(
    api_key=os.getenv("COURSE_LLM_API_KEY"),
    base_url=os.getenv("COURSE_LLM_BASE_URL")
)

def answer_question(question,keyword):
    rows=search_chunks(keyword)
    parts=[]
    source=[]
    for row in rows:
        parts.append(row[1])
        source.append({"id":row[0],"content":row[1]})
    context="\n".join(parts)
    
    prompt=(
    "你是课程资料的问答助手,请只根据以下资料回答问题。\n"
    "如果资料中没有答案，请明确说不知道\n"
    "资料：\n"
    +context
    +"\n问题:\n"
    +question
    )
    
    response=client.chat.completions.create(
        model=os.getenv("COURSE_LLM_MODEL"),
        messages=[{"role":"user","content":prompt}]
    )
    
    answer=response.choices[0].message.content
    return{"answer":answer,"source":source}