import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import numpy as np
import os
from dotenv import load_dotenv
load_dotenv()

# Set page configuration
st.set_page_config(page_title="My Work Journal", page_icon="📋", layout="wide")

# Page header
st.write("# My Work Journal")

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = "/Users/aqaralife/git_projects/aqara_app/.streamlit/doorlock-432423-390c2bdfb237.json"

# Load credentials from the JSON file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Google Sheet ID and Worksheet name
SPREADSHEET_ID = '1gbNuaUov6oAljr0Bf9F049TS0NbBL-oaR3UtmFbhnmg'
WORKSHEET_NAME = '2024'

# Open the worksheet
sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)

# Get current date and time
current_time = datetime.now()

# MySQL 연결 설정
conn = mysql.connector.connect(
    user =  os.getenv('SQL_USER'),
    password =  os.getenv('SQL_PASSWORD'),
    host =  os.getenv('SQL_HOST'),
    database =  os.getenv('SQL_DATABASE'),   # 비밀번호
    charset='utf8mb4',       # UTF-8의 하위 집합을 사용하는 문자셋 설정
    collation='utf8mb4_general_ci'  # 일반적인 Collation 설정
)
conn.autocommit = True
cursor = conn.cursor()

# Create form fields for the user input
st.subheader("Fill in your work journal")

# Registered date field (default is current time)
registered_date = st.date_input("Select Date", value=current_time)

# Task type selection
task_type = st.selectbox("Select Task Type", ["기술지원", "불량접수","반품", "배송누락", "설치주소지변경", "기타"])

# 작업자 선택
worker = st.selectbox("Name", ["이상현", "기타"])

# MySQL에서 동일한 날짜와 업무유형을 가진 데이터 검색
registered_date_for_query = registered_date.strftime('%Y-%m-%d')  # 시간 제외
cursor.execute("""
    SELECT 업무유형, 작업자, 업무일지, 비고 
    FROM work_journal 
    WHERE DATE(registered_date) = %s AND 업무유형 = %s
""", (registered_date_for_query, task_type))

existing_data = cursor.fetchone()

# 만약 기존 데이터가 있으면 폼에 자동으로 채워 넣음
if existing_data:
    st.info("Existing entry found. Fields are pre-filled.")
    work_journal = st.text_area("Write your work journal", value=existing_data[2], height=200)
    note = st.text_area("Notes", value=existing_data[3], height=50)
else:
    work_journal = st.text_area("Write your work journal", height=200)
    note = st.text_area("Notes", height=50)

# 구글 시트에서 기존 데이터 검색
sheet_data = sheet.get_all_values()
df_sheet = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

# 구글 시트에 동일한 등록 날짜와 업무유형을 가진 데이터 검색
matching_rows = df_sheet[(df_sheet['registered_date'] == registered_date_for_query) & (df_sheet['업무유형'] == task_type)]

# Submit button to save to Google Sheets and MySQL
if st.button("Save to Google Sheets and MySQL"):
    # Format the date to string format that can be written to Google Sheets
    registered_date_str = registered_date.strftime('%Y-%m-%d')

    # 새로운 데이터 행
    new_row = [registered_date_str, task_type, worker, work_journal, note]

    # 구글 시트에 동일한 데이터가 있을 경우 업데이트, 없을 경우 추가
    if not matching_rows.empty:
        # 업데이트할 행 번호 찾기 (구글 시트는 1부터 시작하므로 +2)
        row_index = matching_rows.index[0] + 2
        sheet.update(f'A{row_index}:E{row_index}', [new_row])
        st.success("The work journal has been updated in Google Sheets!")
    else:
        # 새로운 행 추가
        sheet.append_row(new_row)
        st.success("The work journal has been saved to Google Sheets!")

    # MySQL 등록 날짜는 시간/분/초를 00:00:00으로 설정
    registered_date_for_db = datetime.combine(registered_date, datetime.min.time())

    # MySQL에서 동일한 날짜와 업무유형이 있는지 확인
    cursor.execute("""
        SELECT id FROM work_journal 
        WHERE DATE(registered_date) = %s AND 업무유형 = %s
    """, (registered_date_for_query, task_type))

    existing_entry = cursor.fetchone()

    if existing_entry:
        # 기존 데이터가 있으면 업데이트
        cursor.execute("""
            UPDATE work_journal 
            SET 작업자 = %s, 업무일지 = %s, 비고 = %s 
            WHERE id = %s
        """, (worker, work_journal, note, existing_entry[0]))
        st.success("The work journal has been updated in MySQL!")
    else:
        # 새로운 데이터 삽입
        cursor.execute("""
            INSERT INTO work_journal (registered_date, 업무유형, 작업자, 업무일지, 비고) 
            VALUES (%s, %s, %s, %s, %s)
        """, (registered_date_for_db, task_type, worker, work_journal, note))
        st.success("The work journal has been saved to MySQL!")

# Fetch the sheet data to display the current data in the sheet
data = sheet.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0])

# Display the updated DataFrame in Streamlit
st.dataframe(df)

# Close MySQL connection
cursor.close()
conn.close()