from app.database import list_chunks,save_embeddings,load_embeddings
from sentence_transformers import SentenceTransformer,util,CrossEncoder
from rank_bm25 import BM25Okapi
import numpy as np

model=SentenceTransformer("BAAI/bge-small-zh-v1.5")
reranker=CrossEncoder("BAAI/bge-reranker-base") 

def make_bigrams(text):
    result=[]
    for i in range(len(text)-1):
        result.append(text[i:i+2])
    return result
        
def rebuild_embeddings():
    rows=list_chunks()
    if not rows:
        return 0
    vectors=model.encode([row[1] for row in rows])
    pairs=[]
    for i,row in enumerate(rows):
        pairs.append((row[0],vectors[i].tobytes()))
    save_embeddings(pairs)
    return len(rows)

def get_embedding_map():
    cached=load_embeddings()
    result={}
    for chunk_id,embedding in cached:
        result[chunk_id]=np.frombuffer(embedding,dtype=np.float32)
    return result

def hybrid_search(question,top=5):
    rows=list_chunks()
    if not rows:
        return []
    
    docs_tokens=[make_bigrams(row[1]) for row in rows]
    bm25=BM25Okapi(docs_tokens)
    bm25_scores=bm25.get_scores(make_bigrams(question))

    vec_by_id=get_embedding_map()
    if len(vec_by_id) == len(rows):
        embeddings=np.array([vec_by_id[row[0]] for row in rows])
    else:
        embeddings=model.encode([row[1] for row in rows])
    query_embedding=model.encode([question])
    vec_scores=util.cos_sim(query_embedding,embeddings)
    
    bm25_rank={}
    sorted_bm25=sorted(range(len(rows)),key=lambda x:bm25_scores[x],reverse=True)
    for rank,i in enumerate(sorted_bm25,start=1):
        bm25_rank[i]=rank
        
    vec_rank={}
    sorted_vec=sorted(range(len(rows)),key=lambda x:vec_scores[0][x],reverse=True)
    for rank,i in enumerate(sorted_vec,start=1):
        vec_rank[i]=rank
        
    fused=[]
    for i in range(len(rows)):
        score=0
        if i in bm25_rank:
            score+=1/(60+bm25_rank[i])
        if i in vec_rank:
            score+=1/(60+vec_rank[i])
        fused.append((rows[i],score))
    fused.sort(key=lambda x:x[1],reverse=True)
    return fused[:top]

def rerank(question,top=5):
    candidates=hybrid_search(question,top=20)
    pairs=[(question,candidate[0][1]) for candidate in candidates]
    scores=reranker.predict(pairs)
    candidates=sorted(zip(candidates,scores),key=lambda x:x[1],reverse=True)
    return [(candidate[0],float(score)) for candidate,score in candidates[:top]]
    
    
