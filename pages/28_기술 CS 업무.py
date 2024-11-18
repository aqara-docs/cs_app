import streamlit as st
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

# MySQL 데이터베이스에 연결하는 함수
def create_connection():
    try:
        connection = mysql.connector.connect(
            user =  os.getenv('SQL_USER'),
            password =  os.getenv('SQL_PASSWORD'),
            host =  os.getenv('SQL_HOST'),
            database =  os.getenv('SQL_DATABASE'),   # 비밀번호
            charset='utf8mb4',       # UTF-8의 하위 집합을 사용하는 문자셋 설정
            collation='utf8mb4_general_ci'  # 일반적인 Collation 설정
        )
        if connection.is_connected():
            return connection
    except Error as e:
        st.error(f"Error while connecting to MySQL: {e}")
        return None

# 기존 데이터를 가져오는 함수
def fetch_existing_data(registered_date, platform, customer, phone):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
            SELECT * FROM cs_table 
            WHERE registered_date = %s AND platform = %s AND customer = %s AND phone = %s
            """
            cursor.execute(query, (registered_date, platform, customer, phone))
            existing_data = cursor.fetchone()
            return existing_data
        except Error as e:
            st.error(f"Failed to fetch data from MySQL table: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return None

# 데이터베이스에 데이터 삽입 또는 업데이트하는 함수
def insert_or_update_data(registered_date, platform, cs_code, customer, phone, device_name, question, answer, status, is_update=False):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            if is_update:
                update_query = """
                UPDATE cs_table 
                SET cs_code = %s, device_name = %s, question = %s, answer = %s, status = %s
                WHERE registered_date = %s AND platform = %s AND customer = %s AND phone = %s
                """
                cursor.execute(update_query, (cs_code, device_name, question, answer, status, registered_date, platform, customer, phone))
                st.success("Data updated successfully")
            else:
                insert_query = """
                INSERT INTO cs_table (registered_date, platform, cs_code, customer, phone, device_name, question, answer, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (registered_date, platform, cs_code, customer, phone, device_name, question, answer, status))
                st.success("Data inserted successfully")
            connection.commit()
        except Error as e:
            st.error(f"Failed to insert/update data in MySQL table: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

# Streamlit UI
st.title("기술 CS 등록")

# 날짜 입력
registered_date = st.date_input("Registered Date", value=datetime.now())

# 플랫폼 선택
platform = st.selectbox("Platform", ["Channel Talk", "Cafe 24", "Naver", "Samsung", "Coupang", "Others"])

# 고객 이름과 전화번호 입력
customer = st.text_input("Customer")
phone = st.text_input("Phone")

# 기존 데이터 가져오기
existing_data = None
if registered_date and platform and customer and phone:
    existing_data = fetch_existing_data(registered_date, platform, customer, phone)
    if existing_data:
        st.info("기존 데이터를 불러왔습니다. 필요한 항목을 수정하세요.")
    else:
        st.info("새로운 데이터를 입력하세요.")

# CS 코드 선택
cs_code = st.selectbox("CS Code", ["SW-AQARA", "SW-Homekit", "SW-Smartthings", "HW-Installation", "General-Question"], index=["SW-AQARA", "SW-Homekit", "SW-Smartthings", "HW-Installation", "General-Question"].index(existing_data['cs_code']) if existing_data else 0)

# 장치 이름 선택
device_name = st.selectbox("Device Name", ["Hub-E1", "Hub-M2", "Hub-M3", "Light-DualRelayModule", "Motor-Blinder","Doorlock-K100","Common"], index=["Hub-E1", "Hub-M2", "Hub-M3", "Light-DualRelayModule", "Motor-Blinder","Doorlock-K100","Common"].index(existing_data['device_name']) if existing_data else 0)

# 질문과 답변 입력
question = st.text_area("Question", value=existing_data['question'] if existing_data else "")
answer = st.text_area("Answer", value=existing_data['answer'] if existing_data else "")

# 상태 체크박스
status = st.checkbox("Status", value=existing_data['status'] if existing_data else False)

# 데이터 제출
if st.button("Submit"):
    insert_or_update_data(registered_date, platform, cs_code, customer, phone, device_name, question, answer, status, is_update=bool(existing_data))