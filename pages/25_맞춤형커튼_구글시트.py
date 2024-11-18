import mysql.connector
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import os
from dotenv import load_dotenv
load_dotenv()

# Set page configuration
st.set_page_config(page_title="맞춤형 커튼 블라인드 관리 대장", page_icon="📋", layout="wide")

# Page header
st.write("# 맞춤형 커튼 블라인드 관리 대장")

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# Load credentials from the JSON file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[os.getenv('SCOPES')])

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Google Sheet ID and Worksheet name
CURTAIN_SPREADSHEET_ID = os.getenv('CURTAIN_SPREADSHEET_ID')
CURTAIN_WORKSHEET_NAME = os.getenv('CURTAIN_WORKSHEET_NAME')  # Replace with your worksheet name


# Open the worksheet
sheet = gc.open_by_key(CURTAIN_SPREADSHEET_ID).worksheet(CURTAIN_WORKSHEET_NAME)

# Fetch all data from the sheet
data = sheet.get_all_values()

# Extract the first 17 columns from each row
data = [row[:17] for row in data]

# Extract the header (first row)
header = data[0]

# Convert data to a DataFrame, excluding the header row
df = pd.DataFrame(data[1:], columns=header)

# Rename columns "665" to "플랫폼" and "날짜" to "registered_date"
df.rename(columns={'665': '플랫폼', '날짜': 'registered_date'}, inplace=True)

# Filter rows where both '플랫폼' and '상품주문번호' columns are not empty or NaN, and exclude '본사 촬영용'
df = df[df['플랫폼'].notna() & df['플랫폼'].str.strip().astype(bool) &
        df['상품주문번호'].notna() & df['상품주문번호'].str.strip().astype(bool) &
        (df['상품주문번호'] != '본사 촬영용')]

# Reset the index and drop the old index
df.reset_index(drop=True, inplace=True)

# Function to adjust the year based on the row index
def adjust_year(date_str, index):
    try:
        # Parse the date assuming it's in 'month/day' format
        date_obj = datetime.strptime(date_str, "%m/%d")
    except ValueError:
        return None
    
    # Assign the correct year based on the row index
    if index <= 262:
        return date_obj.replace(year=2023)
    else:
        return date_obj.replace(year=2024)

# Apply the function to 'registered_date' to convert to datetime with year adjustment
df['registered_date'] = df.apply(lambda row: adjust_year(row['registered_date'], row.name), axis=1)

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

# SQL INSERT 쿼리 (ON DUPLICATE KEY UPDATE)
insert_query = """
    INSERT INTO curtain_ledger 
    (registered_date, 플랫폼, 상품주문번호, 상품명, 수량, 수취인명, 수취인연락처1, 
     수취인연락처2, 배송지, 구매자연락처, 우편번호, 배송메세지, 옵션정보, 
     옵션관리코드, 배송방법, 택배사, 송장번호)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    registered_date = VALUES(registered_date),
    플랫폼 = VALUES(플랫폼),
    상품명 = VALUES(상품명),
    수량 = VALUES(수량),
    수취인명 = VALUES(수취인명),
    수취인연락처1 = VALUES(수취인연락처1),
    수취인연락처2 = VALUES(수취인연락처2),
    배송지 = VALUES(배송지),
    구매자연락처 = VALUES(구매자연락처),
    우편번호 = VALUES(우편번호),
    배송메세지 = VALUES(배송메세지),
    옵션정보 = VALUES(옵션정보),
    옵션관리코드 = VALUES(옵션관리코드),
    배송방법 = VALUES(배송방법),
    택배사 = VALUES(택배사),
    송장번호 = VALUES(송장번호)
"""

# 트랜잭션 재시도 횟수
retry_count = 3

# 각 행의 값을 삽입
for index, row in df.iterrows():
    # 수량이 빈 값이거나 숫자로 변환할 수 없으면 0으로 처리
    try:
        quantity = int(row['수량']) if row['수량'].strip() else 0
    except ValueError:
        quantity = 0

    values = (
        row['registered_date'], row['플랫폼'], row['상품주문번호'], row['상품명'], 
        quantity, row['수취인명'], row['수취인연락처1'], row['수취인연락처2'], 
        row['배송지'], row['구매자연락처'], row['우편번호'], row['배송메세지'], 
        row['옵션정보'], row['옵션관리코드'], row['배송방법'], row['택배사'], row['송장번호']
    )
    for attempt in range(retry_count):
        try:
            cursor.execute(insert_query, values)
            break  # 성공 시 루프 탈출
        except mysql.connector.Error as err:
            if err.errno == 1205:  # Lock wait timeout
                st.write(f"Lock wait timeout, 재시도 중: {attempt + 1}")
                time.sleep(2)  # 잠시 대기 후 재시도
            else:
                raise  # 다른 오류 발생 시

# 연결 종료
cursor.close()
conn.close()

st.write("데이터가 성공적으로 MySQL에 저장되었거나 업데이트되었습니다.")