from pydantic import BaseModel


class QuestionRequest(BaseModel):
    question: str


request = QuestionRequest(question="什么是死锁？")

print(request)
print(request.question)
print(type(request))

try:
    QuestionRequest(question=123)
except ValueError as error:
    print("校验失败：", error)