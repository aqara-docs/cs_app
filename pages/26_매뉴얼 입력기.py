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

# Insert or Update query
query = """
INSERT INTO manual (
    registered_date, title, contents
) VALUES (
    %s, %s, %s
) ON DUPLICATE KEY UPDATE
    registered_date = VALUES(registered_date),
    contents = VALUES(contents)
"""

# title에 따른 contents 조회
def fetch_contents_by_title(title):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    query = "SELECT contents FROM manual WHERE title=%s"
    cursor.execute(query, (title,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else ""

def insert_or_update_data(df):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    try:
        for index, row in df.iterrows():
            cursor.execute(query, (row['registered_date'], row['title'], row['contents']))
        conn.commit()
        st.write("데이터가 성공적으로 MySQL에 저장되었거나 업데이트되었습니다.")
    except Error as e:
        st.write(f"Error while connecting to MySQL: {e}")
    finally:
        cursor.close()
        conn.close()

# 제목에서 'Manual - 숫자' 부분 제거
def clean_title(title):
    return re.sub(r"Manual\s*-\s*\d+", "", title).strip()

# DB에서 title 리스트 가져오기
def fetch_titles_from_db():
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT title FROM `manual`")
    titles = cursor.fetchall()
    cursor.close()
    conn.close()
    return [title[0] for title in titles]

# Streamlit app to upload HTML file
st.title("HTML 문서로부터 데이터 추출 및 DB 저장")

# 1. HTML 파일 업로드 후 처리
uploaded_file = st.file_uploader("HTML 파일을 업로드하세요", type=["html"])

if uploaded_file is not None:
    file_content = uploaded_file.read().decode("utf-8")
    soup = BeautifulSoup(file_content, 'html.parser')

    # HTML의 <title> 태그 가져오기
    html_title = soup.title.string if soup.title else "No Title"
    # 'Manual - 숫자' 부분 제거
    clean_html_title = clean_title(html_title)

    # <p> 및 <td> 태그의 내용 추출
    contents = []
    for tag in soup.find_all(['p', 'td']):
        contents.append(tag.get_text(separator=" ").strip())

    # <p>와 <td> 태그의 내용을 하나의 텍스트로 합치기
    contents_text = " ".join(contents)

    # 현재 날짜와 함께 데이터 저장
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    data = [[today, clean_html_title, contents_text]]

    # DataFrame으로 변환
    df = pd.DataFrame(data, columns=["registered_date", "title", "contents"])

    # DataFrame을 먼저 표시
    st.subheader("추출된 데이터")
    st.dataframe(df)

    # MySQL에 데이터 삽입 또는 업데이트
    if st.button("DB에 저장"):
        insert_or_update_data(df)
        st.write(f"HTML 파일에서 추출된 데이터가 DB에 저장되었습니다: Title - {clean_html_title}")

# 2. 직접 title, contents 입력 폼 추가
st.subheader("Manual 데이터 직접 입력")

# DB에서 title 리스트 가져오기
existing_titles = fetch_titles_from_db()
existing_titles.insert(0, "새로운 제목 입력")  # '새로운 제목 입력' 선택 항목 추가

# title 선택 (기존 제목을 선택하거나 새로 입력)
selected_title = st.selectbox("기존 제목 선택 또는 새로운 제목 입력", existing_titles)

# 기존 제목 선택 시 해당하는 내용을 DB에서 가져옴
if selected_title != "새로운 제목 입력":
    new_title = selected_title
    existing_contents = fetch_contents_by_title(new_title)
else:
    new_title = st.text_input("새로운 제목 입력")
    existing_contents = ""

# contents 입력 (기존 데이터가 있으면 채워짐)
new_contents = st.text_area("내용 입력", value=existing_contents)

# 저장 버튼
if st.button("직접 입력 데이터 저장"):
    if new_title and new_contents:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        data = [[today, new_title, new_contents]]

        # DataFrame으로 변환
        df = pd.DataFrame(data, columns=["registered_date", "title", "contents"])

        # DataFrame을 먼저 표시
        st.subheader("직접 입력된 데이터")
        st.dataframe(df)

        # MySQL에 데이터 삽입 또는 업데이트
        insert_or_update_data(df)
    else:
        st.write("제목과 내용을 모두 입력해주세요.")