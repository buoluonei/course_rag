import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

class DatabaseUnavailableError(RuntimeError):
    pass

def get_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("COURSE_DB_HOST","localhost"),
            user="root",
            password=os.getenv("COURSE_DB_PASSWORD"),
            database="course_rag"
        )
    except mysql.connector.Error as e:
        raise DatabaseUnavailableError("数据库连接失败") from e
    
def save_question(question,answer,session_id=None):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("INSERT INTO questions(question,answer,session_id) VALUES(%s,%s,%s)",(question,answer,session_id))
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
    
    cursor.execute("SELECT chunks.id,chunks.content,documents.filename,chunks.chunk_index,chunks.section_title,chunks.page_number FROM chunks JOIN documents ON chunks.document_id=documents.id ORDER BY chunks.document_id,chunks.chunk_index")
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

def find_document_by_filename(filename):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("SELECT id FROM documents WHERE filename=%s",(filename,))
    rows=cursor.fetchall()
    
    cursor.close()
    connection.close()
    return rows[0][0] if rows else None

def list_question_history(session_id):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("SELECT question,answer FROM questions WHERE session_id=%s ORDER BY id ASC",(session_id,))
    rows=cursor.fetchall()
    
    cursor.close()
    connection.close()
    return rows
    
def save_embeddings(pairs):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("DELETE FROM chunk_embeddings")
    cursor.executemany("INSERT INTO chunk_embeddings(chunk_id,embedding) VALUES(%s,%s)",pairs)
    connection.commit()
    
    cursor.close()
    connection.close()
    
def load_embeddings():
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("SELECT chunk_id,embedding FROM chunk_embeddings")
    rows=cursor.fetchall()
    
    cursor.close()
    connection.close()
    return rows
    
def replace_document(filename,chunks,existing_id=None):
    connection=get_connection()
    cursor=connection.cursor()       
    
    try:
        connection.start_transaction()
        if existing_id is None:
            cursor.execute("INSERT INTO documents(filename) VALUES(%s)",(filename,))
            document_id=cursor.lastrowid
        else:
            cursor.execute("SELECT id FROM documents WHERE id=%s FOR UPDATE",(existing_id,))
            if cursor.fetchone() is None:
                raise ValueError("文档不存在")
            document_id=existing_id
            cursor.execute("DELETE FROM chunks WHERE document_id=%s",(document_id,))
        chunk_rows=[(chunk.text,document_id,chunk.chunk_index,chunk.section_title,chunk.page_number) for chunk in chunks]
        cursor.executemany("INSERT INTO chunks(content,document_id,chunk_index,section_title,page_number) VALUES(%s,%s,%s,%s,%s)",chunk_rows)
        connection.commit()
        return document_id
    
    except mysql.connector.Error as error:
        connection.rollback()
        raise DatabaseUnavailableError("文档保存失败") from error
    
    except Exception:
        connection.rollback()
        raise
    
    finally:
        cursor.close()
        connection.close()