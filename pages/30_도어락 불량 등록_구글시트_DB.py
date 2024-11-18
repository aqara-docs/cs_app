import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from sqlalchemy import create_engine, text
import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()

# Set page configuration
st.set_page_config(page_title="도어락 불량 및 문의 접수 현황", page_icon="📋", layout="wide")

# Page header
st.write("# 도어락 불량 및 문의 접수 현황")

# Google Sheets API authentication and connection
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

# MariaDB connection details
db_user = os.getenv('SQL_USER')
db_password = os.getenv('SQL_PASSWORD')
db_host = os.getenv('SQL_HOST')
db_database = os.getenv('SQL_DATABASE')

# Create SQLAlchemy engine with charset and collation settings
engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_database}?charset=utf8mb4&collation=utf8mb4_general_ci")

# Function to fetch existing data by mobile number from MySQL
def fetch_existing_data(mobile):
    with engine.connect() as conn:
        query = text("SELECT * FROM doorlock_malfunction_ledger WHERE 고객연락처=:mobile")
        existing_data = pd.read_sql(query, con=conn, params={"mobile": mobile})
        if not existing_data.empty:
            return existing_data.iloc[0].to_dict()
        return None

# Function to update or insert data into Google Sheets
def update_google_sheet(sheet, new_row):
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
    df = df.dropna(subset=['registered_date', '고객연락처'], how='all')
    matching_rows = df[(df['registered_date'] == new_row[0]) & (df['고객연락처'] == new_row[4])]
    matching = (df['registered_date'] == new_row[0]) & (df['고객연락처'] == new_row[4])
    print(f"matching_rows is {matching_rows}, matching:{matching}")
    # Find the first row where '고객 연락처' is empty
    #empty_row = df[df['고객연락처'].isnull()].index.min()
    #print(f"비교일:{df['registered_date']}, 연락처:{df['고객연락처']}")
    
    print(f"등록일:{new_row[0]}, 고객연락처:{new_row[4]}")
   

    def find_first_empty_contact_row(sheet):
    # Fetch all the rows of the sheet
        data = sheet.get_all_values()
    # Iterate through the rows starting from row 3 (assuming the first two rows are headers)
        for idx, row in enumerate(data[2:], start=60):  # Start index from 3 because the actual data starts from the third row
            if not row[5]:  # Assuming '고객연락처' is the 6th column (index 5)
                return idx  # Return the 1-based row index where '고객연락처' is empty
        return None 
    
    first_empty_row = find_first_empty_contact_row(sheet)

    if not matching_rows.empty:  # If an empty row is found
        row_index = matching_rows.index[0] + 7   # Adjust for Google Sheets 1-based index (assuming 1 row is header)
        # Insert the data at the correct row
        new_row[0] = new_row[0].replace("-",".")
        sheet.update(f'C{row_index}:N{row_index}', [new_row])  # Update the empty row with new data
        st.success(f"Google Sheets의 {row_index}번째 행에 데이터가 성공적으로 추가되었습니다.")
    else:
        #sheet.append_row(new_row)  # Append new data if no empty row is found
        new_row = ["",""] + new_row
        new_row[2] = new_row[2].replace("-",".")
        sheet.insert_row(new_row,first_empty_row)
        print(first_empty_row)
        print(new_row)
        st.success("새로운 데이터가 Google Sheets에 추가되었습니다.")

    st.dataframe(df)

# User inputs
mobile = st.text_input("고객연락처", "010-xxxx-xxxx")
if mobile:
    existing_data = fetch_existing_data(mobile)

    if existing_data:
        st.info("기존 데이터를 불러왔습니다. 필요한 항목을 수정하세요.")
        
    else:
        st.info("새로운 데이터를 입력하세요.")
        
    if existing_data:
        registered_date = st.date_input("등록 날짜", existing_data['registered_date'])
    else:
        registered_date = st.date_input("등록 날짜", datetime.now().date())
    # Process registered_date
    #registered_date = st.date_input("등록 날짜", datetime.now().date())
    #registered_datetime = datetime.combine(registered_date, datetime.min.time())  # Combine date with time for datetime

    # Form inputs
    channel_options = ["설치기사", "자사톡", "솔리티 AS"]
    clerk_options = ["송지용", "김경일", "신정인", "이상현"]
    malfunction_code_options = [
        "P-001(데드볼트 동작 이상)", "P-002(푸쉬-풀 핸들 동작시 모티스 데드볼트 동작이 안됨)", "P-003(전원 무감)",
        "P-004(비상 전원 (9V) 인가시 무감)", "P-005(도어락 해정 방법으로 문 해정 불가 (지문, 비번, NFC 와 BT 연결도 안됨)",
        "S-001(지문 인식/등록 불가)", "S-002(NFC 카드 인식 불가)", "S-003(10키 터치 불가)", "S-004(10키 중 특정 번호 터치 불가)",
        "S-005(10키 중 특정 LED 점등 불량)", "S-006(R 버튼 무감)", "S-007(수동잠금 버튼 무감)", "S-008(아웃바디 Reset 버튼 무감)",
        "S-009(Aqara App 연동 불량)", "S-010(스마트싱스 연동 불량)", "S-011(Hub 연동 불량)", "S-012(터치음, 메뉴 멘트 등 미출력)",
        "S-013(스트라이크와 데드볼트 간섭으로 문 개방시 뻑뻑함)", "S-014(등록 및 초기화시 관리자 등록 비밀번호 분실로 초기화 및 등록 못함)",
        "S-015(건전지 삽입 후 전면 10키 터치시 LED 안 들어옴. 터치음만 발생하고 LED 미점등)", "E-001(제품 외관 스크래치, 찍힘, 파손 등)",
        "E-002(제품 포장재 파손)", "E-003(사용자가 제품 사용법을 몰라 정상 사용을 못함)"
    ]

    # Select box for 접수 채널 with correct indexing
    if existing_data:
        channel_index = channel_options.index(existing_data['접수채널'])
    else:
        channel_index = 0
    channel = st.selectbox("접수 채널", channel_options, index=channel_index)

    # Select box for 접수자 with correct indexing
    if existing_data:
        clerk_index = clerk_options.index(existing_data['접수자'])
    else:
        clerk_index = 0
    clerk = st.selectbox("접수자", clerk_options, index=clerk_index)

    # Select box for 불량 Code with correct indexing
    if existing_data:
        malfunction_code_index = malfunction_code_options.index(existing_data['불량code'])
    else:
        malfunction_code_index = 0
    

    malfunction_code = st.selectbox("불량 Code", malfunction_code_options, index=malfunction_code_index)
  

    customer = st.text_input("고객명", value=existing_data['고객명'] if existing_data else "")
    disty = st.text_input("설치 대리점", value=existing_data['설치대리점'] if existing_data else "")
    claim = st.text_area("고객 클레임", value=existing_data['고객불량증상'] if existing_data else "")
    action = st.text_area("CS 대응", value=existing_data['조치및대응내용'] if existing_data else "")
    status = st.text_area("진행 상태", value=existing_data['진행상태'] if existing_data else "")
    result = st.checkbox("종결 유무 (Completed)", value=bool(existing_data['종결']) if existing_data else False)
    notice = st.text_area("비고", value=existing_data['비고'] if existing_data else "")

    # Save button
    if st.button("Save Data"):
        data_mysql = {
            'registered_date': registered_date, '접수채널': channel, '접수자': clerk, 
            '고객명': customer, '고객연락처': mobile, '설치대리점': disty, '불량code': malfunction_code, 
            '고객불량증상': claim, '조치및대응내용': action, '진행상태': status, '종결': int(result), '비고': notice
        }

        data_google_sheet = [
            registered_date.strftime("%Y-%m-%d"), channel, clerk, customer, mobile, disty,
            malfunction_code, claim, action, status, result, notice
        ]

        # MySQL update or insert using SQLAlchemy
        with engine.begin() as conn:
            if existing_data:
                # Update existing record in MySQL
                update_query = text("""
                UPDATE doorlock_malfunction_ledger 
                SET registered_date = :registered_date, 접수채널 = :접수채널, 접수자 = :접수자, 고객명 = :고객명, 
                    설치대리점 = :설치대리점, 불량code = :불량code, 고객불량증상 = :고객불량증상, 
                    조치및대응내용 = :조치및대응내용, 진행상태 = :진행상태, 종결 = :종결, 비고 = :비고 
                WHERE 고객연락처 = :고객연락처
                """)
                conn.execute(update_query, data_mysql)
                st.success("기존 데이터가 성공적으로 업데이트되었습니다.")
            else:
                # Insert new record into MySQL
                insert_query = text("""
                INSERT INTO doorlock_malfunction_ledger (
                    registered_date, 접수채널, 접수자, 고객명, 고객연락처, 설치대리점, 
                    불량code, 고객불량증상, 조치및대응내용, 진행상태, 종결, 비고
                ) VALUES (
                    :registered_date, :접수채널, :접수자, :고객명, :고객연락처, :설치대리점, 
                    :불량code, :고객불량증상, :조치및대응내용, :진행상태, :종결, :비고
                )
                """)
                conn.execute(insert_query, data_mysql)
                st.success("새로운 도어락 불량 접수가 등록되었습니다.")

            # Google Sheets update
        update_google_sheet(sheet, data_google_sheet)