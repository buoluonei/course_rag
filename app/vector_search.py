from app.database import list_chunks
from sentence_transformers import SentenceTransformer,util

model=SentenceTransformer("BAAI/bge-small-zh-v1.5")

def search(question,top=5):
    rows=list_chunks()
    if not rows:
        return []
    embeddings=model.encode([row[1] for row in rows])
    query_embedding=model.encode([question])
    similarities=util.cos_sim(query_embedding,embeddings)
    result=[]
    for i in range(len(rows)):
        result.append((rows[i],float(similarities[0][i])))
    top_5=sorted(result,key=lambda x:x[1],reverse=True)[:top]
    return top_5


    
    
    
