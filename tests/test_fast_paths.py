import numpy as np
from fastapi.testclient import TestClient
from app import main, vector_search


def test_greeting_skips_retrieval_and_is_recorded(monkeypatch):
    saved = []
    monkeypatch.setattr(main, 'save_question', lambda *args: saved.append(args))
    response = TestClient(main.app).post('/answers', json={'question': '  你好！  '})
    assert response.status_code == 200
    assert '你好' in response.json()['answer']
    assert response.json()['source'] == []
    assert len(saved) == 1


def test_document_vectors_are_reused_and_invalidated(monkeypatch):
    calls = []
    class Encoder:
        def encode(self, texts):
            calls.append(list(texts))
            return np.ones((len(texts), 2), dtype=np.float32)
    monkeypatch.setattr(vector_search, 'vector_cache_key', None)
    monkeypatch.setattr(vector_search, 'vector_cache', None)
    monkeypatch.setattr(vector_search, 'get_embedding_map', lambda: {})
    monkeypatch.setattr(vector_search, 'get_encoder', lambda: Encoder())
    rows = [(1, '第一段')]
    vector_search.get_document_embeddings(rows)
    vector_search.get_document_embeddings(rows)
    assert len(calls) == 1
    vector_search.get_document_embeddings([(1, '内容发生变化')])
    assert len(calls) == 2
    vector_search.make_index_dirty()
    vector_search.get_document_embeddings(rows)
    assert len(calls) == 3
