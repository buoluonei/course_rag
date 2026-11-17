from app.schemas.question import QuestionRequest


def test_question_request_keeps_the_question() -> None:
    request = QuestionRequest(question="什么是死锁？")

    assert request.question == "什么是死锁？"

