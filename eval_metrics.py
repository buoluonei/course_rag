import numpy as np
from rank_bm25 import BM25Okapi

from app.database import list_chunks
from app.vector_search import (
    get_embedding_map,
    get_encoder,
    hybrid_search,
    make_bigrams,
    rerank,
    util,
)


QUESTIONS = [
    {"question": "如何预防死锁", "relevant_ids": {26, 37, 903}},
    {"question": "怎么避免进程互相等待", "relevant_ids": {26, 37, 903, 905}},
    {"question": "死锁产生的原因是什么", "relevant_ids": {902, 904}},
    {"question": "MySQL 用什么存储引擎", "relevant_ids": {38}},
    {"question": "什么是不可剥夺条件", "relevant_ids": {904}},
    {"question": "死锁的四个必要条件是什么", "relevant_ids": {902, 903, 904}},
]


def bm25_search(question, top=5):
    rows = list_chunks()
    docs_tokens = [make_bigrams(row[1]) for row in rows]
    bm25 = BM25Okapi(docs_tokens)
    scores = bm25.get_scores(make_bigrams(question))
    ranked = sorted(zip(rows, scores), key=lambda item: item[1], reverse=True)
    return [row[0] for row, _ in ranked[:top]]


def vector_search(question, top=5):
    rows = list_chunks()
    vec_by_id = get_embedding_map()
    if len(vec_by_id) == len(rows):
        embeddings = np.array([vec_by_id[row[0]] for row in rows])
    else:
        embeddings = get_encoder().encode([row[1] for row in rows])
    query_embedding = get_encoder().encode([question])
    scores = util.cos_sim(query_embedding, embeddings)[0]
    ranked = sorted(zip(rows, scores), key=lambda item: item[1], reverse=True)
    return [row[0] for row, _ in ranked[:top]]


def recall_at_5(result_ids, relevant_ids):
    hits = sum(1 for chunk_id in result_ids if chunk_id in relevant_ids)
    return hits / len(relevant_ids)


def reciprocal_rank(result_ids, relevant_ids):
    for rank, chunk_id in enumerate(result_ids, start=1):
        if chunk_id in relevant_ids:
            return 1 / rank
    return 0


def evaluate(name, search_fn):
    recalls = []
    ranks = []
    for item in QUESTIONS:
        result_ids = search_fn(item["question"])
        recalls.append(recall_at_5(result_ids, item["relevant_ids"]))
        ranks.append(reciprocal_rank(result_ids, item["relevant_ids"]))
    print(
        f"{name:16s} Recall@5={sum(recalls)/len(recalls):.3f} "
        f"MRR={sum(ranks)/len(ranks):.3f}"
    )


if __name__ == "__main__":
    evaluate("BM25", bm25_search)
    evaluate("向量检索", vector_search)
    evaluate("混合检索", lambda q: [row[0] for row, _ in hybrid_search(q, top=5)])
    evaluate(
        "混合+重排序",
        lambda q: [row[0] for row, _ in rerank(q, top=5)],
    )
