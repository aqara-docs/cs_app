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
st.set_page_config(page_title="판매 리스트 설치 포함", page_icon="📋", layout="wide")

# Page header
st.write("# 도어락 설치 관리 장부")

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# Load credentials from the JSON file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[os.getenv('SCOPES')])

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Google Sheet ID and Worksheet name
DOORLOCK_INSTALLATION_SPREADSHEET_ID = os.getenv('DOORLOCK_INSTALLATION_SPREADSHEET_ID')
DOORLOCK_INSTALLATION_WORKSHEET_NAME = os.getenv('DOORLOCK_INSTALLATION_WORKSHEET_NAME')  # Replace with your worksheet name


# Open the worksheet
sheet = gc.open_by_key(DOORLOCK_INSTALLATION_SPREADSHEET_ID).worksheet(DOORLOCK_INSTALLATION_WORKSHEET_NAME)

# Fetch the sheet data
data = sheet.get_all_values()

# Create a DataFrame, assuming the first two rows are header and instruction rows
# and the actual data starts from the 3rd row (index 2)
df = pd.DataFrame(data[1:])
df = df.iloc[:,1:22]

required_columns =[
    'registered_date', '주문처', '지역1', '지역2', '지점', '설치', '기사연락처',
    '비용', '청구월', '증빙유형', '추가비용', '청구월2', '지급기안', '설치여부','이름', 
    '연락처', '주소', '상품명', '상품옵션', '배송메시지', '특이사항'
]

df.columns = required_columns
#st.dataframe(df)
# Convert the registered_date column to datetime format
# First, try to parse in standard format, if failed, try the specific format 'YYYY. M. D'
#df['registered_date'] = pd.to_datetime(df['registered_date'], errors='coerce')
# Convert the registered_date column to datetime format
# Convert the registered_date column to datetime format
def parse_registered_date(date_str):
    # Define possible formats to try
    date_formats = ['%Y/ %m/ %d', '%Y/%m/%d', '%Y. %m. %d','%Y. %m.%d']
    
    for date_format in date_formats:
        try:
            # Try parsing the date in different formats
            return pd.to_datetime(date_str, format=date_format, errors='raise')
        except (ValueError, TypeError):
            # If it fails, continue to the next format
            continue
    # If all formats fail, return None
    return None

# Apply the function to the 'registered_date' column
df['registered_date'] = df['registered_date'].apply(parse_registered_date)

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
INSERT INTO doorlock_installation_ledger (
    registered_date, 주문처, 지역1, 지역2, 지점, 설치, 기사연락처,
    비용, 청구월, 증빙유형, 추가비용, 청구월2, 지급기안, 설치여부, 이름, 
    연락처, 주소, 상품명, 상품옵션, 배송메시지, 특이사항
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s
) ON DUPLICATE KEY UPDATE
    주문처 = VALUES(주문처),
    지역1 = VALUES(지역1),
    지역2 = VALUES(지역2),
    지점 = VALUES(지점),
    설치 = VALUES(설치),
    기사연락처 = VALUES(기사연락처),
    비용 = VALUES(비용),
    청구월 = VALUES(청구월),
    증빙유형 = VALUES(증빙유형),
    추가비용 = VALUES(추가비용),
    청구월2 = VALUES(청구월2),
    지급기안 = VALUES(지급기안),
    설치여부 = VALUES(설치여부),
    이름 = VALUES(이름),
    상품명 = VALUES(상품명),
    상품옵션 = VALUES(상품옵션),
    배송메시지 = VALUES(배송메시지),
    특이사항 = VALUES(특이사항);
"""

def clean_cost_value(value):
    """비용 또는 추가비용에서 ₩와 ,를 제거하고, 숫자가 아닌 경우 None으로 반환"""
    if isinstance(value, str):
        # ₩와 , 제거
        cleaned_value = value.replace('₩', '').replace(',', '')
        # 숫자인지 확인
        if cleaned_value.isdigit():
            return float(cleaned_value)
        else:
            return None  # 숫자가 아니면 None 반환
    return None if pd.isna(value) else value
# MySQL에 데이터 삽입/업데이트
def insert_or_update_data(df):
    try:
        for index, row in df.iterrows():
            # 상품명, 상품옵션, 배송메시지, 특이사항을 None으로 변경
            values = [
                row['registered_date'].strftime('%Y-%m-%d %H:%M:%S') if row['registered_date'] else None,
                row['주문처'] if row['주문처'] else None,
                row['지역1'] if row['지역1'] else None,
                row['지역2'] if row['지역2'] else None,
                row['지점'] if row['지점'] else None,
                row['설치'] if row['설치'] else None,
                row['기사연락처'] if row['기사연락처'] else None,
                clean_cost_value(row['비용']),  # 비용 처리 함수 적용
                row['청구월'] if row['청구월'] else None,
                row['증빙유형'] if row['증빙유형'] else None,
                clean_cost_value(row['추가비용']),  # 추가비용 처리 함수 적용
                row['청구월2'] if row['청구월2'] else None,
                row['지급기안'] if row['지급기안'] else None,
                1 if row['설치여부'] == 'TRUE' else 0,
                row['이름'] if row['이름'] else None,
                row['연락처'] if row['연락처'] else None,
                row['주소'] if row['주소'] else None,
                row['상품명'] if row['상품명'] else None,
                row['상품옵션'] if row['상품옵션'] else None,
                row['배송메시지'] if row['배송메시지'] else None,
                row['특이사항'] if row['특이사항'] else None
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