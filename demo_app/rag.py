import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import APIError, OpenAI

from demo_app.database import count_chunks, search_chunks


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

client = OpenAI(
    api_key=os.getenv("COURSE_LLM_API_KEY"),
    base_url=os.getenv("COURSE_LLM_BASE_URL"),
)


class ModelServiceUnavailableError(Exception):
    pass


def _question_terms(question):
    text = re.sub(r"[^\w\u4e00-\u9fff]", "", question.lower())
    stopwords = {"什么", "为什么", "如何", "怎么", "是否", "可以", "需要", "应该"}
    terms = set()
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", text))
    for stopword in stopwords:
        chinese = chinese.replace(stopword, "")
    terms.update(
        chinese[index : index + 2]
        for index in range(len(chinese) - 1)
    )
    terms.update(re.findall(r"[a-z0-9]+", text))
    return [term for term in terms if term]


def answer_question(question):
    rows = search_chunks(_question_terms(question))
    if not rows and count_chunks() == 0:
        return None

    if not rows:
        return {
            "answer": "资料中没有答案。",
            "sources": [],
            "source_count": 0,
        }

    sources = []
    parts = []
    for row in rows:
        sources.append({"id": row[0], "content": row[1]})
        parts.append(row[1])

    context = "\n\n".join(parts)
    prompt = (
        "你是课程资料问答助手。请只根据以下资料回答问题。"
        "如果资料中没有答案，请明确回答：资料中没有答案。\n\n"
        "资料：\n"
        + context
        + "\n\n问题：\n"
        + question
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("COURSE_LLM_MODEL"),
            messages=[{"role": "user", "content": prompt}],
        )
    except APIError as error:
        raise ModelServiceUnavailableError() from error

    return {
        "answer": response.choices[0].message.content,
        "sources": sources,
        "source_count": len(sources),
    }
