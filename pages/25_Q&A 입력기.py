import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
load_dotenv()

# MySQL 연결 설정
def get_mysql_connection():
    return mysql.connector.connect(
        user=os.getenv('SQL_USER'),
        password=os.getenv('SQL_PASSWORD'),
        host=os.getenv('SQL_HOST'),
        database=os.getenv('SQL_DATABASE'),
        charset='utf8mb4',
        collation='utf8mb4_general_ci'
    )

# DB에서 기존의 title 리스트 가져오기
def fetch_titles():
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT title FROM qna")
    titles = cursor.fetchall()
    cursor.close()
    conn.close()
    return [title[0] for title in titles]

# DB에서 title과 question이 같은 경우, answer 가져오기
def fetch_answer(title, question):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    query = "SELECT answer FROM qna WHERE title=%s AND question=%s"
    cursor.execute(query, (title, question))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else ""

# Insert or Update query
query = """
INSERT INTO qna (
    registered_date, title, question, answer
) VALUES (
    %s, %s, %s, %s
) ON DUPLICATE KEY UPDATE
    registered_date = VALUES(registered_date),
    answer = VALUES(answer)
"""

def insert_or_update_data(data):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    try:
        for row in data:
            cursor.execute(query, row)
        conn.commit()
        st.write("데이터가 성공적으로 MySQL에 저장되었거나 업데이트되었습니다.")
    except Error as e:
        st.write(f"Error while connecting to MySQL: {e}")
    finally:
        cursor.close()
        conn.close()

# Streamlit app to upload HTML file
st.title("질문과 답변 추출기")

# 1. HTML 파일 업로드 후 처리
uploaded_file = st.file_uploader("HTML 파일을 업로드하세요", type=["html"])

if uploaded_file is not None:
    file_content = uploaded_file.read().decode("utf-8")
    soup = BeautifulSoup(file_content, 'html.parser')

    html_title = soup.title.string if soup.title else "No Title"
    callouts = soup.find_all('div', class_='callout-body-container')

    data = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for callout in callouts:
        question = None
        answer = None
        for strong_tag in callout.find_all('strong'):
            strong_text = strong_tag.get_text().strip()

            if "질문" in strong_text:
                question = strong_tag.find_parent().get_text(separator=" ").strip()

            if "답변" in strong_text:
                answer_parts = []
                answer_tag = strong_tag.find_parent()
                while answer_tag and (answer_tag.name == 'p' or answer_tag.name == 'ul'):
                    answer_parts.append(answer_tag.get_text(separator=" ").strip())
                    answer_tag = answer_tag.find_next_sibling()
                answer = " ".join(answer_parts).strip()

        if question and answer:
            data.append([today, html_title, question, answer])

    df = pd.DataFrame(data, columns=["registered_date", "title", "question", "answer"])
    insert_or_update_data(df.values.tolist())
    st.write("HTML 파일에서 추출된 데이터가 DB에 저장되었습니다.")

# 2. 직접 title, question, answer 입력 폼 추가
st.subheader("Q&A 직접 입력")

# DB에서 가져온 title 리스트를 selectbox로 표시
existing_titles = fetch_titles()
selected_title = st.selectbox("기존 제목을 선택하세요", options=["직접 입력"] + existing_titles)

if selected_title == "직접 입력":
    new_title = st.text_input("새로운 제목 입력")
else:
    new_title = selected_title

# question 입력
new_question = st.text_input("질문 입력")

# DB에 동일한 title과 question이 있을 경우, answer 가져오기
if selected_title != "직접 입력" and new_question:
    existing_answer = fetch_answer(new_title, new_question)
    if existing_answer:
        st.write("기존 답변을 불러왔습니다.")
else:
    existing_answer = ""

# answer 입력
new_answer = st.text_area("답변 입력", value=existing_answer)

# 저장 버튼
if st.button("저장"):
    if new_title and new_question and new_answer:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        data = [[today, new_title, new_question, new_answer]]
        insert_or_update_data(data)
    else:
        st.write("모든 필드를 채워주세요.")