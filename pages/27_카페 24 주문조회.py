import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import re
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import numpy as np


load_dotenv()

# Set page configuration
st.set_page_config(page_title="카페24 주문 조회", page_icon="📋", layout="wide")

# Page header
st.write("# 카페24 주문조회")

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# Load credentials from the JSON file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[os.getenv('SCOPES')])

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Google Sheet ID and Worksheet name
DOORLOCK_INSTALLATION_SPREADSHEET_ID = os.getenv('CAFE24_SPREADSHEET_ID')
DOORLOCK_INSTALLATION_WORKSHEET_NAME = os.getenv('CAFE24_WORKSHEET_NAME')

# Open the worksheet
sheet = gc.open_by_key(DOORLOCK_INSTALLATION_SPREADSHEET_ID).worksheet(DOORLOCK_INSTALLATION_WORKSHEET_NAME)

# Fetch the sheet data
data = sheet.get_all_values()

# Create a DataFrame, assuming the first row is the header
df = pd.DataFrame(data[1:], columns=data[0])

# 1. 주문일(결제일) 칼럼 처리: 괄호 안의 데이터를 삭제하고 datetime형으로 변환
df['registered_date'] = df['registered_date'].str.replace(r"\(.*\)", "", regex=True).str.strip()
df['registered_date'] = pd.to_datetime(df['registered_date'], format="%Y-%m-%d %H:%M:%S", errors='coerce')

# 2. 주문번호 칼럼 처리: xxxxxxxx-xxxxxxx 형태의 데이터만 유지 및 "/ xxxx-xxxxxxx" 형태의 데이터 수정
def clean_order_number(order_number):
    # 패턴을 찾고, 없으면 빈 문자열로 대체
    match = re.search(r"\d{8}-\d{7}", order_number)
    return match.group() if match else ""

df['주문번호'] = df['주문번호'].apply(clean_order_number)

# 3. 주문자 칼럼 처리: 첫 번째 공백 전까지만 남기기
df['주문자'] = df['주문자'].apply(lambda x: x.split()[0] if pd.notna(x) and len(x.split()) > 0 else "")

# Loop through the dataframe and append the odd row (홀수 row) to the even row (짝수 row)
for i in range(0, len(df), 2):
    if i + 1 < len(df):
        # Append 홀수 row to 짝수 row in the '수령자' column
        df.at[i, '수령자'] = df.iloc[i + 1, 0]

# Drop the 홀수 rows
df = df.drop(index=[i for i in range(1, len(df), 2)])

# Reset the index after row removal
df.reset_index(drop=True, inplace=True)
df = df.iloc[:,1:]
# NaN 값을 None으로 변환
df = df.replace({np.nan: None})

# Display the DataFrame in Streamlit
st.dataframe(df)
#duplicated_rows = df[df.duplicated(subset='주문번호', keep=False)]
#st.write("중복된 주문번호가 있는 행:", duplicated_rows)
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
INSERT INTO cafe24_order (
    registered_date, 주문번호, 주문자, 상품명, 수령자
) VALUES (
    %s, %s, %s, %s, %s
) ON DUPLICATE KEY UPDATE
    registered_date = VALUES(registered_date),
    주문자 = VALUES(주문자),
    상품명 = VALUES(상품명),
    수령자 = VALUES(수령자);
"""


# MySQL에 데이터 삽입/업데이트
def insert_or_update_data(df):
    try:
        for index, row in df.iterrows():
            # 상품명, 상품옵션, 배송메시지, 특이사항을 None으로 변경
            values = [
                row['registered_date'].strftime('%Y-%m-%d %H:%M:%S') if row['registered_date'] else None,
                row['주문번호'] if row['주문번호'] else None,
                row['주문자'] if row['주문자'] else None,
                row['상품명'] if row['상품명'] else None,
                row['수령자'] if row['수령자'] else None
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