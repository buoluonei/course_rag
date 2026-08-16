import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("COURSE_DB_PASSWORD"),
        database="course_rag",
    )


def ensure_tables():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS demo_chunks ("
        "id INT AUTO_INCREMENT PRIMARY KEY, "
        "content TEXT NOT NULL"
        ")"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS demo_questions ("
        "id INT AUTO_INCREMENT PRIMARY KEY, "
        "question TEXT NOT NULL, "
        "answer TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ")"
    )
    connection.commit()
    cursor.close()
    connection.close()


def replace_chunks(chunks):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM demo_chunks")
    for chunk in chunks:
        cursor.execute(
            "INSERT INTO demo_chunks (content) VALUES (%s)",
            (chunk,),
        )

    connection.commit()
    cursor.close()
    connection.close()


def list_chunks(limit=10):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id, content FROM demo_chunks ORDER BY id ASC LIMIT %s",
        (limit,),
    )
    rows = cursor.fetchall()

    cursor.close()
    connection.close()
    return rows


def search_chunks(terms, limit=8):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id, content FROM demo_chunks")
    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    ranked = []
    for row in rows:
        content = row[1].lower()
        score = sum(content.count(term.lower()) for term in terms if term)
        ranked.append((score, row[0], row[1]))

    ranked = [item for item in ranked if item[0] > 0]
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [(item[1], item[2]) for item in ranked[:limit]]


def count_chunks():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM demo_chunks")
    row = cursor.fetchone()

    cursor.close()
    connection.close()
    return row[0]


def save_question(question, answer):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO demo_questions (question, answer) VALUES (%s, %s)",
        (question, answer),
    )
    connection.commit()

    cursor.close()
    connection.close()


def list_questions(limit, offset):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id, question, answer, created_at "
        "FROM demo_questions ORDER BY id DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )
    rows = cursor.fetchall()

    cursor.close()
    connection.close()
    return rows


def count_questions():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM demo_questions")
    row = cursor.fetchone()

    cursor.close()
    connection.close()
    return row[0]


def get_question_by_id(question_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id, question, answer, created_at "
        "FROM demo_questions WHERE id = %s",
        (question_id,),
    )
    row = cursor.fetchone()

    cursor.close()
    connection.close()
    return row


def delete_question(question_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM demo_questions WHERE id = %s", (question_id,))
    deleted_count = cursor.rowcount
    connection.commit()

    cursor.close()
    connection.close()
    return deleted_count
