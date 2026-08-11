from app.database import replace_chunks

file=open("data/course.txt","r",encoding="utf-8")
content=file.read()
file.close()

chunks=[]
for line in content.split("\n"):
    if line!="":
        chunks.append(line)

replace_chunks(chunks)
print("替换完成",len(chunks))
