from app import vector_search


def test_encoder_is_loaded_once(monkeypatch) -> None:
    instances = []

    class FakeEncoder:
        pass

    def fake_loader(name):
        instance = FakeEncoder()
        instances.append((name, instance))
        return instance

    monkeypatch.setattr(vector_search, "encoder", None)
    monkeypatch.setattr(vector_search, "SentenceTransformer", fake_loader)

    first = vector_search.get_encoder()
    second = vector_search.get_encoder()

    assert first is second
    assert instances == [("BAAI/bge-small-zh-v1.5", first)]


def test_reranker_is_loaded_once(monkeypatch) -> None:
    instances = []

    class FakeReranker:
        pass

    def fake_loader(name):
        instance = FakeReranker()
        instances.append((name, instance))
        return instance

    monkeypatch.setattr(vector_search, "reranker", None)
    monkeypatch.setattr(vector_search, "CrossEncoder", fake_loader)

    first = vector_search.get_reranker()
    second = vector_search.get_reranker()

    assert first is second
    assert instances == [("BAAI/bge-reranker-base", first)]


def test_rebuild_embeddings_clears_cache_when_no_chunks(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(vector_search, "list_chunks", lambda: [])
    monkeypatch.setattr(vector_search, "save_embeddings", calls.append)

    result = vector_search.rebuild_embeddings()

    assert result == 0
    assert calls == [[]]
