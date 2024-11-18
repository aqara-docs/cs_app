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
st.set_page_config(page_title="신규사업 파트너 검색", page_icon="📋", layout="wide")

# Page header
st.write("# 신규사업 파트너 검색")

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# Load credentials from the JSON file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[os.getenv('SCOPES')])

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Google Sheet ID and Worksheet name
NEW_PARTNERS_CANDIDATES_SPREADSHEET_ID = os.getenv('NEW_PARTNERS_CANDIDATES_SPREADSHEET_ID')
NEW_PARTNERS_CANDIDATES_SPREADSHEET_NAME = os.getenv('NEW_PARTNERS_CANDIDATES_SPREADSHEET_NAME')  # Replace with your worksheet name



# Open the worksheet
sheet = gc.open_by_key(NEW_PARTNERS_CANDIDATES_SPREADSHEET_ID).worksheet(NEW_PARTNERS_CANDIDATES_SPREADSHEET_NAME)

# Fetch the sheet data
data = sheet.get_all_values()

# Create a DataFrame, assuming the first two rows are header and instruction rows
# and the actual data starts from the 3rd row (index 2)
df = pd.DataFrame(data[1:])
df = df.iloc[:, 0:10]

# Define the required columns
required_columns = [
    '등록일','분야', '회사', '회사소개', '웹사이트', '연락처', '제품범주', 
    '제품명', '제품특징', '비고'
]
df.columns = required_columns
df['등록일'] = pd.to_datetime(df['등록일'], errors='coerce')

# Replace empty strings with None
df = df.replace("", None)
# Step 1: 분야 선택
selected_field = st.selectbox("분야 선택", options=["전체"] + df['분야'].unique().tolist())

# Step 2: 분야에 맞는 회사 리스트 업데이트
if selected_field != "전체":
    companies = df[df['분야'] == selected_field]['회사'].unique().tolist()
else:
    companies = df['회사'].unique().tolist()

selected_company = st.selectbox("회사 선택", options=["전체"] + companies)

# Step 3: 회사와 분야에 맞는 제품 범주 리스트 업데이트
if selected_field != "전체" and selected_company != "전체":
    product_categories = df[(df['분야'] == selected_field) & (df['회사'] == selected_company)]['제품범주'].unique().tolist()
elif selected_field != "전체":
    product_categories = df[df['분야'] == selected_field]['제품범주'].unique().tolist()
elif selected_company != "전체":
    product_categories = df[df['회사'] == selected_company]['제품범주'].unique().tolist()
else:
    product_categories = df['제품범주'].unique().tolist()

selected_product_category = st.selectbox("제품범주 선택", options=["전체"] + product_categories)

# 검색 버튼
if st.button("검색"):
    # Apply filters
    filtered_df = df.copy()
    
    if selected_field != "전체":
        filtered_df = filtered_df[filtered_df['분야'] == selected_field]
    
    if selected_company != "전체":
        filtered_df = filtered_df[filtered_df['회사'] == selected_company]
    
    if selected_product_category != "전체":
        filtered_df = filtered_df[filtered_df['제품범주'] == selected_product_category]
    
    # 검색 결과 출력
    st.write("## 검색 결과 (테이블)")
    st.table(filtered_df)
    
    
    # 검색 결과를 JSON 형식으로 출력
    st.write("## 검색 결과 (JSON)")
    try:
        # 데이터프레임을 JSON 문자열로 변환
        filtered_json = filtered_df.to_json(orient='records', force_ascii=False, indent=4)
        
        # JSON 데이터를 화면에 출력
        st.text(filtered_json)
    except TypeError as e:
        st.write(f"Error: {e}")