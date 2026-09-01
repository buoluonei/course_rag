import numpy as np
from rank_bm25 import BM25Okapi

from app.database import get_connection
from app.vector_search import get_encoder, get_reranker, make_bigrams, util
from eval_chunk_sizes import RELEVANT, hit_ratio, recover_documents, split_text


def fetch_all():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, document_id, content FROM chunks ORDER BY id")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return rows


def build_indexes(chunks):
    tokens = [make_bigrams(chunk) for chunk in chunks]
    bm25 = BM25Okapi(tokens)
    embeddings = get_encoder().encode(chunks)
    return bm25, embeddings


def hybrid_top(question, chunks, bm25, embeddings, top=20):
    bm25_scores = bm25.get_scores(make_bigrams(question))
    query_embedding = get_encoder().encode([question])
    vec_scores = util.cos_sim(query_embedding, embeddings)[0]

    bm25_rank = {
        index: rank
        for rank, index in enumerate(
            sorted(range(len(chunks)), key=lambda i: bm25_scores[i], reverse=True),
            start=1,
        )
    }
    vec_rank = {
        index: rank
        for rank, index in enumerate(
            sorted(range(len(chunks)), key=lambda i: vec_scores[i], reverse=True),
            start=1,
        )
    }

    fused = []
    for index in range(len(chunks)):
        score = 0
        if index in bm25_rank:
            score += 1 / (60 + bm25_rank[index])
        if index in vec_rank:
            score += 1 / (60 + vec_rank[index])
        fused.append((index, score))
    fused.sort(key=lambda item: item[1], reverse=True)
    return [index for index, _ in fused[:top]]


def rerank_top(question, chunks, candidate_indexes, top=5):
    pairs = [(question, chunks[index]) for index in candidate_indexes]
    scores = get_reranker().predict(pairs)
    ranked = sorted(
        zip(candidate_indexes, scores),
        key=lambda item: item[1],
        reverse=True,
    )
    return [index for index, _ in ranked[:top]]


def evaluate_chunk_size(chunk_size, overlap, rows, relevant_texts):
    documents = recover_documents(rows)
    chunks = []
    for text in documents.values():
        chunks.extend(split_text(text, chunk_size, overlap))

    bm25, embeddings = build_indexes(chunks)
    recalls = []
    ranks = []
    for question, answer_ids in RELEVANT.items():
        answers = [relevant_texts[chunk_id] for chunk_id in answer_ids]
        candidates = hybrid_top(question, chunks, bm25, embeddings)
        top_indexes = rerank_top(question, chunks, candidates)

        hit_count = 0
        first_rank = 0
        for rank, index in enumerate(top_indexes, start=1):
            best_ratio = max(hit_ratio(answer, chunks[index]) for answer in answers)
            if best_ratio >= 0.8:
                hit_count += 1
                if first_rank == 0:
                    first_rank = rank
        recalls.append(hit_count / len(answers))
        ranks.append(1 / first_rank if first_rank else 0)

    print(
        f"chunk_size={chunk_size:3d} overlap={overlap:3d} "
        f"chunks={len(chunks):3d} "
        f"Recall@5={sum(recalls)/len(recalls):.3f} "
        f"MRR={sum(ranks)/len(ranks):.3f}"
    )


if __name__ == "__main__":
    rows = fetch_all()
    relevant_texts = {chunk_id: content for chunk_id, _, content in rows}
    for chunk_size in (100, 200, 300):
        evaluate_chunk_size(chunk_size, chunk_size // 5, rows, relevant_texts)
