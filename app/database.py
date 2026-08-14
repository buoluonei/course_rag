import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("COURSE_DB_PASSWORD"),
        database="course_rag"
    )
    
def save_question(question,answer):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("INSERT INTO questions(question,answer) VALUES(%s,%s)",(question,answer))
    connection.commit()
    
    cursor.close()
    connection.close()
    
def list_questions(limit,offset):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("SELECT id,question,created_at,answer FROM questions ORDER BY id DESC LIMIT %s OFFSET %s",(limit,offset))
    rows=cursor.fetchall()    
    
    cursor.close()
    connection.close()
    return rows

def save_chunks(chunks):
    connection=get_connection()
    cursor=connection.cursor()
    
    for chunk in chunks:
        cursor.execute("INSERT INTO chunks(content) VALUES(%s)",(chunk,))
    connection.commit()
    
    cursor.close()
    connection.close()

def search_chunks(key_words):
    connection=get_connection()
    cursor=connection.cursor()
    
    pattern="%"+key_words+"%"
    cursor.execute("SELECT chunks.id,chunks.content,documents.filename FROM chunks JOIN documents ON chunks.document_id=documents.id WHERE content LIKE %s",(pattern,))
    rows=cursor.fetchall()
    
    cursor.close()
    connection.close()
    return rows

def replace_chunks(chunks,document_id):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("DELETE FROM chunks WHERE document_id=%s",(document_id,))
    
    for chunk in chunks:
        cursor.execute("INSERT INTO chunks(content,document_id) VALUES(%s,%s)",(chunk,document_id))
    
    connection.commit()
    cursor.close()
    connection.close()
    
    
def list_chunks():
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("SELECT chunks.id,chunks.content,documents.filename FROM chunks JOIN documents ON chunks.document_id=documents.id")
    rows=cursor.fetchall()
    
    cursor.close()
    connection.close()
    return rows

def get_question_by_id(id):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("SELECT * FROM questions WHERE id=%s",(id,))
    row=cursor.fetchone()
    
    cursor.close()
    connection.close()
    return row

def delete_question(id):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("DELETE FROM questions WHERE id=%s",(id,))
    deleted_count=cursor.rowcount
    connection.commit()
    
    cursor.close()
    connection.close()
    return deleted_count

def count_questions():
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM questions")
    row=cursor.fetchone()
    
    cursor.close()
    connection.close()
    return row[0]

def save_document(filename):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("INSERT INTO documents(filename) VALUES(%s)",(filename,))
    document_id=cursor.lastrowid
    connection.commit()
    
    cursor.close()
    connection.close()
    return document_id

def list_documents():
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("SELECT id,filename,created_at FROM documents ORDER BY id DESC")
    rows=cursor.fetchall()
    
    cursor.close()
    connection.close()
    return rows

def delete_document(document_id):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("DELETE FROM chunks WHERE document_id=%s",(document_id,))
    cursor.execute("DELETE FROM documents WHERE id=%s",(document_id,))
    deleted_count=cursor.rowcount
    connection.commit()
    
    cursor.close()
    connection.close()
    return deleted_count