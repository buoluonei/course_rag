import pytest
from fastapi import HTTPException
from app import rag, vector_search


def test_only_deepseek_key_is_needed(monkeypatch):
    calls = []
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
    monkeypatch.setattr(rag, 'OpenAI', lambda **kwargs: calls.append(kwargs) or object())
    rag.get_deepseek_client()
    assert calls[0]['api_key'] == 'test-key'
    assert calls[0]['base_url'] == 'https://api.deepseek.com'


def test_missing_key_has_clear_error(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    with pytest.raises(HTTPException, match='DeepSeek API Key'):
        rag.get_deepseek_client()


def test_default_search_uses_keyword_without_model(monkeypatch):
    rows = [(1, '死锁是多个进程相互等待资源', 'a.txt', 0, None, None)]
    class FakeBM25:
        def get_scores(self, tokens):
            return [-0.5]
    monkeypatch.setattr(vector_search, 'get_bm25_index', lambda: (FakeBM25(), rows))
    monkeypatch.setattr(vector_search, 'get_encoder', lambda: pytest.fail('不应加载向量模型'))
    monkeypatch.setattr(vector_search, 'get_reranker', lambda: pytest.fail('不应加载重排序模型'))
    assert vector_search.keyword_search('什么是死锁') == [(rows[0], -0.5)]
    assert vector_search.keyword_search('量子通信') == []
