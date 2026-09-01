from app.main import split_chunks


def test_split_chunks_defaults_to_200_with_overlap() -> None:
    text = "字" * 500

    chunks = split_chunks(text)

    assert len(chunks) == 3
    assert all(len(chunk) <= 200 for chunk in chunks)


def test_split_chunks_accepts_custom_size() -> None:
    text = "字" * 300

    chunks = split_chunks(text, chunk_size=100, chunk_overlap=20)

    assert all(len(chunk) <= 100 for chunk in chunks)
    assert len(chunks) > 1


def test_split_chunks_keeps_tail() -> None:
    text = "字" * 250

    chunks = split_chunks(text)

    assert chunks[0] == text[:200]
    assert chunks[-1] == text[160:]
