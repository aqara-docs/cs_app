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
st.set_page_config(page_title="도어락 설치 파트너", page_icon="📋", layout="wide")

# Page header
st.write("# 도어락 설치 파트너")

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# Load credentials from the JSON file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[os.getenv('SCOPES')])

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Google Sheet ID and Worksheet name
DOORLOCK_INSTALLATION__PARTNERS_SPREADSHEET_ID = os.getenv('DOORLOCK_INSTALLATION_PARTNERS_SPREADSHEET_ID')
DOORLOCK_INSTALLATION_PARTNERS_WORKSHEET_NAME = os.getenv('DOORLOCK_INSTALLATION_PARTNERS_WORKSHEET_NAME')  # Replace with your worksheet name



# Open the worksheet
sheet = gc.open_by_key(DOORLOCK_INSTALLATION__PARTNERS_SPREADSHEET_ID).worksheet(DOORLOCK_INSTALLATION_PARTNERS_WORKSHEET_NAME)

# Fetch the sheet data
data = sheet.get_all_values()

# Create a DataFrame, assuming the first two rows are header and instruction rows
# and the actual data starts from the 3rd row (index 2)
df = pd.DataFrame(data[1:])
df = df.iloc[:,1:15]

# Add 'registered_date' column with the date 2024.02.19 in datetime format
registered_date = pd.to_datetime('2024.02.19')
df.insert(0, 'registered_date', registered_date)

required_columns = ['registered_date', '지역1','지역2','대리점','담당자코드','대표','연락처','주소','사업자등록번호','은행','계좌','소유자명','세금계산서','플라자','기타']
df.columns = required_columns

# Replace empty strings or spaces in '연락처' with NaN
df['연락처'] = df['연락처'].replace(r'^\s*$', np.nan, regex=True)
# Remove rows where '연락처' is missing
df = df.dropna(subset=['연락처'])

# NaN 값을 None으로 변환
df = df.replace({np.nan: None})

# Display the DataFrame in Streamlit
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
INSERT INTO doorlock_installation_partners (
    registered_date, 지역1, 지역2, 대리점, 담당자코드, 대표, 연락처, 주소,
    사업자등록번호, 은행, 계좌, 이름, 세금계산서, 플라자, 기타
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON DUPLICATE KEY UPDATE
    지역1 = VALUES(지역1),
    담당자코드 = VALUES(담당자코드),
    대표 = VALUES(대표),
    연락처 = VALUES(연락처),
    사업자등록번호 = VALUES(사업자등록번호),
    은행 = VALUES(은행),
    계좌 = VALUES(계좌),
    이름 = VALUES(이름),
    세금계산서 = VALUES(세금계산서),
    플라자 = VALUES(플라자),
    기타 = VALUES(기타);
"""

# MySQL에 데이터 삽입/업데이트
def insert_or_update_data(df):
    try:
        for index, row in df.iterrows():
            # 데이터 준비 (문자열에서 None 처리 및 필요하면 변환)
            values = [
                row['registered_date'].strftime('%Y-%m-%d %H:%M:%S') if row['registered_date'] else None,
                row['지역1'] if row['지역1'] else None,
                row['지역2'] if row['지역2'] else None,
                row['대리점'] if row['대리점'] else None,
                row['담당자코드'] if row['담당자코드'] else None,
                row['대표'] if row['대표'] else None,
                row['연락처'] if row['연락처'] else None,
                row['주소'] if row['주소'] else None,
                row['사업자등록번호'] if row['사업자등록번호'] else None,
                row['은행'] if row['은행'] else None,
                row['계좌'] if row['계좌'] else None,
                row['소유자명'] if row['소유자명'] else None,  # '이름'으로 변경 가능
                row['세금계산서'] if row['세금계산서'] else None,
                row['플라자'] if row['플라자'] else None,
                row['기타'] if row['기타'] else None
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