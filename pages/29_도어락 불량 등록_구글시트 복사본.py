import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import numpy as np
import os
from dotenv import load_dotenv
load_dotenv()

# Set page configuration
st.set_page_config(page_title="도어락 불량 및 문의 접수 현황", page_icon="📋", layout="wide")

# Page header
st.write("# 도어락 불량 및 문의 접수 현황")

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# Load credentials from the JSON file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[os.getenv('SCOPES')])

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Google Sheet ID and Worksheet name
DOORLOCK_MALFUNCTION_SPREADSHEET_ID = os.getenv('DOORLOCK_MALFUNCTION_SPREADSHEET_ID')
DOORLOCK_MALFUNCTION_WORKSHEET_NAME = os.getenv('DOORLOCK_MALFUNCTION_WORKSHEET_NAME')  # Replace with your worksheet name



# Open the worksheet
sheet = gc.open_by_key(DOORLOCK_MALFUNCTION_SPREADSHEET_ID).worksheet(DOORLOCK_MALFUNCTION_WORKSHEET_NAME)

# Fetch the sheet data
data = sheet.get_all_values()

# Create a DataFrame, assuming the first two rows are header and instruction rows
# and the actual data starts from the 3rd row (index 2)
df = pd.DataFrame(data[6:])
df = df.iloc[:, 2:14]

# Define the required columns
required_columns = [
    'registered_date', '접수채널', '접수자', '고객명', '고객연락처', '설치대리점', 
    '불량code', '고객불량증상', '조치및대응내용', '진행상태', '종결', '비고'
]
df.columns = required_columns

# Replace empty strings with None
df = df.replace("", None)

# Convert the registered_date column to datetime format
df['registered_date'] = pd.to_datetime(df['registered_date'], errors='coerce')

# Remove rows where both '고객명' and '고객불량증상' are missing
df = df.dropna(subset=['고객명', '고객불량증상'], how='all')

# Display the filtered dataframe in Streamlit
st.dataframe(df)

# MySQL 연결 설정
conn = mysql.connector.connect(
        user =  os.getenv('SQL_USER'),
        password =  os.getenv('SQL_PASSWORD'),
        host =  os.getenv('SQL_HOST'),
        database =  os.getenv('SQL_DATABASE'),   # 비밀번호
        charset='utf8mb4',       # UTF-8의 하위 집합을 사용하는 문자셋 설정
        collation='utf8mb4_general_ci'  # 일반적인 Collation 설정
)

# Autocommit 활성화
conn.autocommit = True
cursor = conn.cursor()

# Insert or Update query
query = """
INSERT INTO doorlock_malfunction_ledger (
    registered_date, 접수채널, 접수자, 고객명, 고객연락처, 설치대리점, 불량code, 고객불량증상, 조치및대응내용, 진행상태, 종결, 비고
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON DUPLICATE KEY UPDATE
    접수채널 = VALUES(접수채널),
    접수자 = VALUES(접수자),
    고객명 = VALUES(고객명),
    설치대리점 = VALUES(설치대리점),
    불량code = VALUES(불량code),
    고객불량증상 = VALUES(고객불량증상),
    조치및대응내용 = VALUES(조치및대응내용),
    진행상태 = VALUES(진행상태),
    종결 = VALUES(종결),
    비고 = VALUES(비고);
"""

# MySQL에 데이터 삽입/업데이트
def insert_or_update_data(df):
    try:
        for index, row in df.iterrows():
            values = [
                row['registered_date'].strftime('%Y-%m-%d %H:%M:%S') if row['registered_date'] else None,
                row['접수채널'] if row['접수채널'] else None,
                row['접수자'] if row['접수자'] else None,
                row['고객명'] if row['고객명'] else None,
                row['고객연락처'] if row['고객연락처'] else None,
                row['설치대리점'] if row['설치대리점'] else None,
                row['불량code'] if row['불량code'] else None,
                row['고객불량증상'] if row['고객불량증상'] else None,
                row['조치및대응내용'] if row['조치및대응내용'] else None,
                row['진행상태'] if row['진행상태'] else None,
                1 if row['종결'] == 'TRUE' else 0,
                row['비고'] if row['비고'] else None
            ]
            # 쿼리 실행
            cursor.execute(query, values)
        
        conn.commit()
        st.write("데이터가 성공적으로 MySQL에 저장되었거나 업데이트되었습니다.")
    except Error as e:
        st.write(f"Error while connecting to MySQL: {e}")
    finally:
        cursor.close()
        conn.close()

# df의 데이터를 MySQL에 삽입/업데이트
insert_or_update_data(df)