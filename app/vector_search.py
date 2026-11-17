from app.database import list_chunks,save_embeddings,load_embeddings
from sentence_transformers import SentenceTransformer,util,CrossEncoder
from rank_bm25 import BM25Okapi
import numpy as np

class RetrievalModelUnavailableError(RuntimeError):
    pass

bm25=None
bm25_rows=[]
bm25_index_dirty=True
bm25_index_initialized=False

encoder=None
reranker=None

def get_encoder():
    global encoder
    if encoder is None:
        try:
            # Honor Hugging Face configuration supplied by the environment.
            # On a fresh machine the model may need to be downloaded.
            encoder=SentenceTransformer("BAAI/bge-small-zh-v1.5", device='cpu')
        except Exception as e:
            raise RetrievalModelUnavailableError("向量模型加载失败") from e
    return encoder

def get_reranker():
    global reranker
    if reranker is None:
        try:
            reranker=CrossEncoder("BAAI/bge-reranker-base", device='cpu')
        except Exception as e:
            raise RetrievalModelUnavailableError("重排序模型加载失败") from e
    return reranker

def make_bigrams(text):
    result=[]
    for i in range(len(text)-1):
        result.append(text[i:i+2])
    return result
        
def rebuild_embeddings():
    rows=list_chunks()
    if not rows:
        save_embeddings([])
        return 0
    vectors=get_encoder().encode([row[1] for row in rows])
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

def make_index_dirty():
    global bm25_index_dirty
    bm25_index_dirty=True

def build_bm25_index():
    global bm25,bm25_rows,bm25_index_dirty,bm25_index_initialized
    
    rows=list_chunks()
    docs_tokens=[make_bigrams(row[1]) for row in rows]
    
    if docs_tokens:
        new_bm25=BM25Okapi(docs_tokens)
    else:
        new_bm25=None
    
    bm25=new_bm25
    bm25_rows=rows
    bm25_index_dirty=False
    bm25_index_initialized=True

def get_bm25_index():
    if bm25_index_dirty or not bm25_index_initialized:
        build_bm25_index()
    return bm25,bm25_rows

def hybrid_search(question,top=5):
    bm25,rows=get_bm25_index()
    
    if not rows or bm25 is None:
        return []
    
    bm25_scores=bm25.get_scores(make_bigrams(question))

    vec_by_id=get_embedding_map()
    
    row_ids={row[0] for row in rows}
    cached_ids=set(vec_by_id.keys())
    
    if row_ids==cached_ids:
        embeddings=np.array([vec_by_id[row[0]] for row in rows])
    else:
        embeddings=get_encoder().encode([row[1] for row in rows])
    query_embedding=get_encoder().encode([question])
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

def rerank(question,candidate_k=20,final_k=5):
    candidates=hybrid_search(question,top=candidate_k)
    if not candidates:
        return []
    pairs=[(question,candidate[0][1]) for candidate in candidates]
    scores=get_reranker().predict(pairs)
    ranked=sorted(zip(candidates,scores),key=lambda x:x[1],reverse=True)
    return [(candidate[0],float(score)) for candidate,score in ranked[:final_k]]
    
