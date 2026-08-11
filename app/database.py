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
    
def save_question(question):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("INSERT INTO questions(question) VALUES(%s)",(question,))
    connection.commit()
    
    cursor.close()
    connection.close()
    
def list_questions():
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("SELECT id,question FROM questions")
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
    cursor.execute("SELECT * FROM chunks WHERE content LIKE %s",(pattern,))
    rows=cursor.fetchall()
    
    cursor.close()
    connection.close()
    return rows

def replace_chunks(chunks):
    connection=get_connection()
    cursor=connection.cursor()
    
    cursor.execute("DELETE FROM chunks")
    
    for chunk in chunks:
        cursor.execute("INSERT INTO chunks(content) VALUES(%s)",(chunk,))
    
    connection.commit()
    cursor.close()
    connection.close()
