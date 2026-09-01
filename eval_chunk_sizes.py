from rank_bm25 import BM25Okapi

from app.database import get_connection
from app.vector_search import make_bigrams


RELEVANT = {
    "如何预防死锁": [26, 37, 903],
    "怎么避免进程互相等待": [26, 37, 903, 905],
    "死锁产生的原因是什么": [902, 904],
    "MySQL 用什么存储引擎": [38],
    "什么是不可剥夺条件": [904],
    "死锁的四个必要条件是什么": [902, 903, 904],
}


def fetch_all():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, document_id, content FROM chunks ORDER BY id")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return rows


def recover_documents(rows):
    docs = {}
    for chunk_id, document_id, content in rows:
        docs.setdefault(document_id, []).append(content)
    return {doc_id: "\n".join(parts) for doc_id, parts in docs.items()}


def split_text(text, chunk_size, overlap):
    chunks = []
    start = 0
    while start < len(text) - chunk_size:
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    tail = text[start:].strip()
    if tail:
        chunks.append(tail)
    return chunks


def normalize(text):
    return "".join(text.split())


def hit_ratio(answer_text, chunk_text):
    answer = normalize(answer_text)
    chunk = normalize(chunk_text)
    if not answer or not chunk:
        return 0
    if answer in chunk:
        return 1
    best = 0
    for window_size in range(len(answer), 0, -1):
        found = False
        for start in range(0, len(answer) - window_size + 1):
            window = answer[start : start + window_size]
            if window in chunk:
                best = window_size
                found = True
                break
        if found:
            break
    return best / len(answer)


def bm25_top(question, chunks, top=5):
    tokens = [make_bigrams(chunk) for chunk in chunks]
    bm25 = BM25Okapi(tokens)
    scores = bm25.get_scores(make_bigrams(question))
    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    return [chunks[i] for i in ranked[:top]]


def evaluate_chunk_size(chunk_size, overlap, rows, relevant_texts):
    documents = recover_documents(rows)
    all_chunks = []
    for text in documents.values():
        all_chunks.extend(split_text(text, chunk_size, overlap))

    recalls = []
    ranks = []
    for question, answer_ids in RELEVANT.items():
        answers = [relevant_texts[chunk_id] for chunk_id in answer_ids]
        top_chunks = bm25_top(question, all_chunks)
        hit_count = 0
        first_rank = 0
        for rank, chunk in enumerate(top_chunks, start=1):
            best_ratio = max(hit_ratio(answer, chunk) for answer in answers)
            if best_ratio >= 0.8:
                hit_count += 1
                if first_rank == 0:
                    first_rank = rank
        recalls.append(hit_count / len(answers))
        ranks.append(1 / first_rank if first_rank else 0)

    print(
        f"chunk_size={chunk_size:3d} overlap={overlap:3d} "
        f"chunks={len(all_chunks):3d} "
        f"Recall@5={sum(recalls)/len(recalls):.3f} "
        f"MRR={sum(ranks)/len(ranks):.3f}"
    )


if __name__ == "__main__":
    rows = fetch_all()
    relevant_texts = {chunk_id: content for chunk_id, _, content in rows}
    for chunk_size in (100, 200, 300, 500):
        evaluate_chunk_size(chunk_size, chunk_size // 5, rows, relevant_texts)
