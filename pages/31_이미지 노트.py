import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
from PIL import Image
import io
import base64
import os
from datetime import datetime

# MySQL 연결 설정 (dotenv를 사용하여 환경 변수로부터 값 가져오기)
from dotenv import load_dotenv
load_dotenv()

db_user = os.getenv('SQL_USER')
db_password = os.getenv('SQL_PASSWORD')
db_host = os.getenv('SQL_HOST')
db_database = os.getenv('SQL_DATABASE')

# MySQL 연결 함수
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_database,
            charset='utf8mb4',
            collation='utf8mb4_general_ci'
        )
        if connection.is_connected():
            return connection
    except Error as e:
        st.error(f"Error while connecting to MySQL: {e}")
    return connection

# 데이터 저장 함수
def save_to_db(title, description, image):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "INSERT INTO image_note (title, description, image) VALUES (%s, %s, %s)"
            cursor.execute(query, (title, description, image))
            connection.commit()
            st.success("Data has been saved successfully!")
        except Error as e:
            st.error(f"Error while saving to MySQL: {e}")
        finally:
            cursor.close()
            connection.close()

# 날짜, title, description 검색 함수
def fetch_data_by_date_and_keyword(start_date, end_date, keyword):
    connection = create_connection()
    if connection:
        try:
            query = """
                SELECT id, title, description, image, created_at 
                FROM image_note 
                WHERE (DATE(created_at) BETWEEN %s AND %s) 
                AND (title LIKE %s OR description LIKE %s)
                ORDER BY created_at DESC
            """
            # '%' + keyword + '%' 는 SQL의 LIKE 조건을 위한 구문으로, 검색어가 포함된 텍스트를 찾습니다.
            df = pd.read_sql(query, connection, params=(start_date, end_date, f"%{keyword}%", f"%{keyword}%"))
            return df
        except Error as e:
            st.error(f"Error while fetching data from MySQL: {e}")
        finally:
            connection.close()

# 이미지 데이터를 base64로 인코딩 (DB에서 가져온 이미지 표시용)
def image_to_base64(img_blob):
    encoded_img = base64.b64encode(img_blob).decode('utf-8')
    return f"data:image/jpeg;base64,{encoded_img}"

# 이미지 업로드 및 텍스트 입력 폼
st.title("텍스트 및 이미지 저장 앱")
title = st.text_input("제목 입력")
description = st.text_area("설명 입력")
uploaded_file = st.file_uploader("이미지 업로드", type=["jpg", "jpeg", "png"])

if uploaded_file and title and description:
    # 이미지 파일 읽기 및 MySQL에 저장할 수 있도록 변환
    img = uploaded_file.read()  # 파일을 바이너리 데이터로 변환
    if st.button("저장하기"):
        save_to_db(title, description, img)

# 날짜 및 키워드 검색
st.header("날짜 및 키워드 검색")

# 날짜 선택 위젯 (기본값: 오늘 날짜)
start_date = st.date_input("시작 날짜", datetime.now())
end_date = st.date_input("종료 날짜", datetime.now())

# 키워드 입력
keyword = st.text_input("검색할 키워드 입력 (제목 또는 설명)")

if st.button("검색하기"):
    if start_date > end_date:
        st.error("종료 날짜는 시작 날짜보다 이후여야 합니다.")
    else:
        data = fetch_data_by_date_and_keyword(start_date, end_date, keyword)
        if data is not None and not data.empty:
            for idx, row in data.iterrows():
                st.subheader(f"ID: {row['id']} - {row['title']} (작성일: {row['created_at']})")
                st.write(f"설명: {row['description']}")
                # 이미지 표시
                img_html = image_to_base64(row['image'])
                st.markdown(f'<img src="{img_html}" width="200" />', unsafe_allow_html=True)
        else:
            st.write("해당 조건에 맞는 데이터가 없습니다.")