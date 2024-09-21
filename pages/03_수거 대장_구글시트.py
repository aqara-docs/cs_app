import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
from datetime import datetime
import re
import mysql.connector
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
load_dotenv()

# Set page configuration
st.set_page_config(page_title="수거신청대장", page_icon="📋", layout="wide")

# Page header
st.write("# 수거신청대장 관리 시스템")

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# Load credentials from the JSON file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[os.getenv('SCOPES')])

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Google Sheet ID and Worksheet name
SERVICE_SPREADSHEET_ID = os.getenv('SERVICE_SPREADSHEET_ID')
SERVICE_WORKSHEET_NAME = os.getenv('SERVICE_WORKSHEET_NAME')  # Replace with your worksheet name

# Function to make column names unique
def make_unique_columns(columns):
    seen = {}
    for idx, col in enumerate(columns):
        if col in seen:
            seen[col] += 1
            columns[idx] = f"{col}_{seen[col]}"
        else:
            seen[col] = 0
    return columns

# Function to load data from Google Sheets
def load_sheet_data():
    worksheet = gc.open_by_key(SERVICE_SPREADSHEET_ID).worksheet(SERVICE_WORKSHEET_NAME)
    
    # Get all values from the sheet
    all_values = worksheet.get_all_values()
    
    # Skip the first two rows and set the 3rd row as header
    headers = all_values[2]  # Use the 3rd row as the header
    data = all_values[3:]    # Data starts from the 4th row
    
    # Create DataFrame
    df = pd.DataFrame(data, columns=headers)
    df.replace('', np.nan, inplace=True)
    df.dropna(subset=['고객명'], inplace=True)

    # Make column names unique
    df.columns = make_unique_columns(list(df.columns))
    
    return df

# Load the data
df = load_sheet_data()

if not df.empty:
    # Verify the correct column names
    if '작성일' in df.columns:
        # Initialize 'registered_date' column with None
        df['registered_date'] = None
        
        # Attempt to parse dates in multiple formats using regular expressions to detect the format
        for idx, row in df.iterrows():
            date_str = row['작성일']
            
            if pd.isna(date_str):
                continue

            try:
                if re.match(r'^\d{4}\.\d{1,2}\.\d{1,2}$', date_str):
                    # Parse format '%Y.%m.%d'
                    df.at[idx, 'registered_date'] = pd.to_datetime(date_str, format='%Y.%m.%d')
                elif re.match(r'^\d{1,2}/\d{1,2}$', date_str):
                    # Parse format '%m/%d' and add current year
                    parsed_date = pd.to_datetime(date_str, format='%m/%d')
                    parsed_date = parsed_date.replace(year=datetime.now().year)
                    df.at[idx, 'registered_date'] = parsed_date
                elif re.match(r'^\d{4}\.\s?\d{1,2}\.\d{1,2}$', date_str):
                    # Parse format '%Y. %m %d' or '%Y.%m.%d' with optional spaces
                    df.at[idx, 'registered_date'] = pd.to_datetime(date_str, format='%Y. %m.%d')
                elif re.match(r'^\d{4}\.\s?\d{1,2}\s\d{1,2}$', date_str):
                    # Parse format '%Y. %m %d' without periods after the month
                    df.at[idx, 'registered_date'] = pd.to_datetime(date_str, format='%Y. %m %d')
                else:
                    df.at[idx, 'registered_date'] = None  # If format is not matched, set as None
            except Exception as e:
                print(f"Error parsing date {date_str}: {e}")
                df.at[idx, 'registered_date'] = None

        # Remove the original '작성일' column
        df.drop(columns=['작성일'], inplace=True)

        # Reorder columns to move 'registered_date' before '작성자'
        columns = df.columns.tolist()
        if '작성자' in columns:
            author_index = columns.index('작성자')
            columns.insert(author_index, columns.pop(columns.index('registered_date')))
            df = df[columns]

    # Replace NaN values in the DataFrame with None for SQL compatibility
    df.replace({np.nan: None, '': None}, inplace=True)

    # Convert '완료' and '주소변경' to boolean values (1 for TRUE, 0 for FALSE)
    boolean_columns = ['완료', '주소변경']
    for col in boolean_columns:
        if col in df.columns:
            df[col] = df[col].map({'TRUE': 1, 'FALSE': 0, None: 0})  # Convert 'TRUE'/'FALSE' to 1/0, default to 0 if None

    # Ensure all required columns are present and fill missing columns with default values
    required_columns = [
        '완료', 'registered_date', '작성자', '구분', '사유', '배송비', '주문처', '주문번호', '고객명', 
        '연락처', '주소변경', '우편번호', '주소', '제품', '수량', '비고', '수거신청',
        '수거완료', '교환출고', '환불처리', '택배사', 
        '원송장', '반송장', '교환출고송장', '조치'
    ]

    df = df[required_columns]

    # Convert numeric columns to appropriate types
    numeric_columns = ['수량']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Convert datetime columns to appropriate types for MySQL
    datetime_columns = ['registered_date']
    for col in datetime_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    # Display the DataFrame
    st.dataframe(df)

    # MySQL 데이터베이스에 DataFrame 삽입
    try:
        # Create a connection using mysql.connector
        conn = mysql.connector.connect(
            user =  os.getenv('SQL_USER'),
            password =  os.getenv('SQL_PASSWORD'),
            host =  os.getenv('SQL_HOST'),
            database =  os.getenv('SQL_DATABASE'),   # 비밀번호
            charset='utf8mb4',       # UTF-8의 하위 집합을 사용하는 문자셋 설정
            collation='utf8mb4_general_ci'  # 일반적인 Collation 설정
        )

        cursor = conn.cursor()

        # Iterate through each row in the DataFrame
        for idx, row in df.iterrows():
            # Replace NaN with None
            row = row.where(pd.notnull(row), None)

            # Validate date values and set invalid dates to None
            for date_col in ['registered_date']:
                if row[date_col] and not re.match(r'^\d{4}-\d{2}-\d{2}$', str(row[date_col])):
                    row[date_col] = None

            # Ensure key fields are not None or empty
            if not row['registered_date'] or not row['고객명'] or not row['주문번호'] or not row['제품']:
               # st.warning(f"Skipping row {idx} because key fields are missing.")
                continue

            # Define the SQL query to check for existing records
            check_query = """
            SELECT COUNT(*) FROM service_ledger 
            WHERE registered_date = %s AND 고객명 = %s AND 주문번호 = %s AND 제품 = %s
            """
            
            # Execute the query with parameters
            cursor.execute(check_query, (row['registered_date'], row['고객명'], row['주문번호'], row['제품']))
            result = cursor.fetchone()

            if result[0] > 0:
                # If a matching record exists, perform an update
                #st.write(f"Updating record for {row['고객명']} with 주문번호 {row['주문번호']}")
                #st.write("Existing records have been updated!!")
                update_query = """
                UPDATE service_ledger 
                SET 완료 = %s, 작성자 = %s, 구분 = %s, 사유 = %s, 배송비 = %s, 주문처 = %s,
                    연락처 = %s, 주소변경 = %s, 우편번호 = %s, 주소 = %s, 수량 = %s, 비고 = %s, 수거신청 = %s, 
                    수거완료 = %s, 교환출고 = %s, 환불처리 = %s, 택배사 = %s, 원송장 = %s, 
                    반송장 = %s, 교환출고송장 = %s, 조치 = %s
                WHERE registered_date = %s AND 고객명 = %s AND 주문번호 = %s AND 제품 = %s
                """
                
                # Execute the update query
                cursor.execute(update_query, (
                    row['완료'], row['작성자'], row['구분'], row['사유'], row['배송비'], row['주문처'],
                    row['연락처'], row['주소변경'], row['우편번호'], row['주소'], row['수량'], row['비고'], row['수거신청'],
                    row['수거완료'], row['교환출고'], row['환불처리'], row['택배사'], row['원송장'],
                    row['반송장'], row['교환출고송장'], row['조치'],
                    row['registered_date'], row['고객명'], row['주문번호'], row['제품']
                ))
            else:
                # If no matching record exists, perform an insert
                st.write(f"Inserting new record for {row['고객명']} with 주문번호 {row['주문번호']}")
                
                insert_query = """
                INSERT INTO service_ledger (완료, registered_date, 작성자, 구분, 사유, 배송비, 주문처, 주문번호, 고객명, 
                    연락처, 주소변경, 우편번호, 주소, 제품, 수량, 비고, 수거신청,
                    수거완료, 교환출고, 환불처리, 택배사, 원송장, 반송장, 교환출고송장, 조치) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                # Execute the insert query
                cursor.execute(insert_query, (
                    row['완료'], row['registered_date'], row['작성자'], row['구분'], row['사유'], row['배송비'], row['주문처'],
                    row['주문번호'], row['고객명'], row['연락처'], row['주소변경'], row['우편번호'], row['주소'], row['제품'], 
                    row['수량'], row['비고'], row['수거신청'], row['수거완료'], row['교환출고'], row['환불처리'], row['택배사'], row['원송장'], 
                    row['반송장'], row['교환출고송장'], row['조치']
                ))

        # Commit changes to the database
        conn.commit()

        st.success("Data has been successfully inserted or updated in the MySQL database!")

    except Exception as e:
        st.error(f"An error occurred while inserting or updating data in MySQL: {e}")

    finally:
        # Close the connection
        if conn.is_connected():
            cursor.close()
            conn.close()

else:
    st.warning("No data available to process.")