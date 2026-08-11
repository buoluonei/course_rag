from app.database import search_chunks

file=open("data/course.txt","r",encoding="utf-8")
content=file.read()

chunks=content.split("\n")
key_words="死锁"
rows=search_chunks(key_words)
parts=[]
for row in rows:
    parts.append(row[1])
context="\n".join(parts)
print(context)

question="什么是死锁"
prompt=(
    "请只根据下面的资料回答问题。\n"
    "资料:\n"
    +context
    +"\n问题:\n"
    +question
)                 

print(prompt)
