from app.database import get_connection
from rank_bm25 import BM25Okapi
from app.rag import extract_keywords
from app.database import search_chunks

connection = get_connection()          # 1. 连接数据库
cursor = connection.cursor()           # 2. 拿一个"操作手柄"
cursor.execute("SELECT id, content FROM chunks")   # 3. 执行查询：拿所有资料块的 id 和内容
rows = cursor.fetchall()               # 4. 把查询结果全部取回来
cursor.close()                         # 5. 用完手柄，关掉
connection.close()                     # 6. 断开数据库连接

print("资料块总数:", len(rows))        # 7. 打印一共多少块


def make_bigrams(text):                # 8. 切词函数（和 demo 里一样）
    result = []
    for i in range(len(text) - 1):
        result.append(text[i:i+2])
    return result


def old_search(question):
    keywords = extract_keywords(question)
    score={}
    content_by_id={}
    for keyword in keywords:
        matched = search_chunks(keyword)
        for item in matched:
            if item[0] not in score:
                score[item[0]]=0
            score[item[0]]+=item[1].count(keyword)
            content_by_id[item[0]]=item[1]
    ranked=sorted(score.items(),key=lambda x:x[1],reverse=True)
    top=ranked[:5]
    result=[]
    for item in top:
        result.append((item[0],content_by_id[item[0]],item[1]))
    return result
    

docs_tokens = [make_bigrams(row[1]) for row in rows]   # 9. 所有资料切词
bm25 = BM25Okapi(docs_tokens)          # 10. 建 BM25 索引

questions = ["如何预防死锁","怎么避免进程互相等待","死锁产生的原因是什么","MySQL 用什么存储引擎","什么是不可剥夺条件","死锁的四个必要条件是什么"]      
for question in questions:
    # 11. 测试问题
    query_tokens = make_bigrams(question)  # 12. 问题切词
    scores = bm25.get_scores(query_tokens) # 13. 对全部 846 份资料打分

    pairs = []                             # 14. 把 (资料, 分数) 配对
    for i in range(len(rows)):
        pairs.append((rows[i], scores[i]))
    pairs.sort(key=lambda x: x[1], reverse=True)   # 15. 按分数从高到低排序

    print(f"问题：{question}")              # 16. 打印前 3 名
    for row, score in pairs[:5]:
        print(f"分数 {score:.2f} | id={row[0]} | {row[1][:25]}")
        
    print("== 旧方法 ==")
    old_results = old_search(question)
    for chunk_id, content, s in old_results:
        print(f"分数 {s:.2f} | id={chunk_id} | {content[:25]}")    
