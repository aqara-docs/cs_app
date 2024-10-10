import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import mysql.connector
import numpy as np
import os
from dotenv import load_dotenv
import re
load_dotenv()

# Set page configuration
st.set_page_config(page_title="토탈 설치 서비스 관리 대장", page_icon="📋", layout="wide")

# Page header
st.write("# 토털 설치 서비스 관리 장부")

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# Load credentials from the JSON file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[os.getenv('SCOPES')])

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Google Sheet ID and Worksheet name
INSTALLATION_SPREADSHEET_ID = os.getenv('INSTALLATION_SPREADSHEET_ID')
INSTALLATION_WORKSHEET_NAME = os.getenv('INSTALLATION_WORKSHEET_NAME')  # Replace with your worksheet name

# Open the worksheet
sheet = gc.open_by_key(INSTALLATION_SPREADSHEET_ID).worksheet(INSTALLATION_WORKSHEET_NAME)

# Fetch the sheet data
data = sheet.get_all_values()

# Create a DataFrame, assuming the first two rows are header and instruction rows
# and the actual data starts from the 3rd row (index 2)
df = pd.DataFrame(data[2:], columns=[
    'registered_date', '출고날짜', '고객명', '연락처', '주문번호', '주소',
    '도어락', '도어벨', '조명스위치', '커튼', '내용확인', '기사님성함', '해피콜예정일', 
    '설치예정일', '설치완료여부', '구매품목','유상', '비고_아카라', '비고_피엘'
])

# 날짜 형식 처리 함수
def parse_date(date_str):
    if pd.isna(date_str) or not date_str:
        return None
    try:
        # Check if the format is "24.09.23" (dd.mm.yy)
        if re.match(r'^\d{2}\.\d{2}\.\d{2}$', date_str):
            return pd.to_datetime('20' + date_str, format='%Y.%m.%d')  # Assume 20xx century
        else:
            # Try to parse other formats normally
            return pd.to_datetime(date_str, errors='coerce')
    except Exception as e:
        return None

# Convert the registered_date and other relevant date columns
df['registered_date'] = df['registered_date'].apply(parse_date)
df['출고날짜'] = df['출고날짜'].apply(parse_date)
df['해피콜예정일'] = df['해피콜예정일'].apply(parse_date)
df['설치예정일'] = df['설치예정일'].apply(parse_date)

# 빈 날짜를 바로 앞의 날짜로 채워주는 로직
df['registered_date'] = df['registered_date'].fillna(method='ffill')

# Convert columns to appropriate types
numeric_columns = ['도어락', '도어벨', '조명스위치', '커튼']
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Convert boolean columns
boolean_columns = ['내용확인', '설치완료여부']
for col in boolean_columns:
    df[col] = df[col].apply(lambda x: True if x and x.lower() == 'true' else False)

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

cursor = conn.cursor()

# 데이터프레임의 각 행을 MySQL 테이블에 삽입 또는 업데이트 (주문번호가 있는 경우만)
for index, row in df.iterrows():
    # 주문번호가 존재하는 경우에만 삽입 또는 업데이트
    if row['주문번호'] and pd.notna(row['주문번호']):
        sql = """
            INSERT INTO installation_ledger 
            (registered_date, 출고날짜, 고객명, 연락처, 주문번호, 주소,
            도어락, 도어벨, 조명스위치, 커튼, 내용확인, 기사님성함, 해피콜예정일, 
            설치예정일, 설치완료여부, 구매품목,유상, 비고_아카라, 비고_피엘)
            VALUES (%s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            registered_date = VALUES(registered_date),
            출고날짜 = VALUES(출고날짜),
            고객명 = VALUES(고객명),
            연락처 = VALUES(연락처),
            주소 = VALUES(주소),
            도어락 = VALUES(도어락),
            도어벨 = VALUES(도어벨),
            조명스위치 = VALUES(조명스위치),
            커튼 = VALUES(커튼),
            내용확인 = VALUES(내용확인),
            기사님성함 = VALUES(기사님성함),
            해피콜예정일 = VALUES(해피콜예정일),
            설치예정일 = VALUES(설치예정일),
            설치완료여부 = VALUES(설치완료여부),
            구매품목 = VALUES(구매품목),
            유상 = VALUES(유상),
            비고_아카라 = VALUES(비고_아카라),
            비고_피엘 = VALUES(비고_피엘)
        """
        values = (
            row['registered_date'], row['출고날짜'], row['고객명'], row['연락처'], row['주문번호'], row['주소'],
            row['도어락'], row['도어벨'], row['조명스위치'], row['커튼'], row['내용확인'], row['기사님성함'], row['해피콜예정일'],
            row['설치예정일'], row['설치완료여부'], row['구매품목'],row['유상'], row['비고_아카라'], row['비고_피엘']
        )
        
        cursor.execute(sql, values)

# 변경 사항을 커밋하고 연결을 닫음
conn.commit()
cursor.close()
conn.close()

st.write("주문번호에 따라 데이터가 성공적으로 삽입 또는 업데이트되었습니다.")