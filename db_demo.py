import os
import mysql.connector
from dotenv import load_dotenv
from app.database import save_question,list_questions
# load_dotenv()
# password = os.getenv("COURSE_DB_PASSWORD")
# value="coach"
# connection=mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password=password,
#     database="course_rag"
# )

# save_question(value)
print(list_questions())