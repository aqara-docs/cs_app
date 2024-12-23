import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set Streamlit page configuration
st.set_page_config(page_title="Weekly Journal", page_icon="📋", layout="wide")

# Page header
st.title("Weekly Journal")

# Google Sheets connection
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)

# Google Sheets settings
WEEKLY_SPREADSHEET_ID = os.getenv('WEEKLY_SPREADSHEET_ID')
WEEKLY_WORKSHEET_NAME = os.getenv('WEEKLY_WORKSHEET_NAME')
sheet = gc.open_by_key(WEEKLY_SPREADSHEET_ID).worksheet(WEEKLY_WORKSHEET_NAME)

# MySQL connection
conn = mysql.connector.connect(
   user=os.getenv('SQL_USER'),
   password=os.getenv('SQL_PASSWORD'),
   host=os.getenv('SQL_HOST'),
   database=os.getenv('SQL_DATABASE_NEWBIZ'),
   charset='utf8mb4',
   collation='utf8mb4_general_ci'
)
conn.autocommit = True
cursor = conn.cursor()

# Get current date and calculate date range for the previous week
current_date = datetime.now()
start_of_prev_week = (current_date - timedelta(days=current_date.weekday())).date()
end_of_prev_week = start_of_prev_week + timedelta(days=6)

# Display current date and calculated week range
st.write(f"Current Date: {current_date.strftime('%Y-%m-%d')}")
st.write(f"Previous Week Range: {start_of_prev_week} to {end_of_prev_week}")

# User input form
st.subheader("Fill in your weekly journal")

# Date input
등록일 = st.date_input("등록일", value=current_date)

# Task type
task_type = st.selectbox("업무유형", ["미팅", "파트너 컨택", "기술 검토", "DB/AI", "기타"])

# Worker selection
worker = st.selectbox("담당자", ["김현철", "이지이", "장창환", "이상현", "기타"])

# Fetch previous week's data from both tables
# 1. work_journal에서 전주 업무 내역 가져오기
cursor.execute("""
   SELECT 등록일, 업무일지 
   FROM work_journal 
   WHERE 등록일 BETWEEN %s AND %s AND 업무유형 = %s AND 작업자 = %s
   ORDER BY 등록일 ASC
""", (start_of_prev_week, end_of_prev_week, task_type, worker))

prev_week_work_logs = cursor.fetchall()

# 2. weekly_journal에서 동일 기간의 금주업무 가져오기
cursor.execute("""
   SELECT 등록일, 금주업무 
   FROM weekly_journal 
   WHERE 등록일 BETWEEN %s AND %s AND 업무유형 = %s AND 작업자 = %s
   ORDER BY 등록일 ASC
""", (start_of_prev_week, end_of_prev_week, task_type, worker))

this_week_logs = cursor.fetchall()

# 전주업무 내역 조합
if prev_week_work_logs:
   previous_week_summary = "\n".join([f"[{log[0].strftime('%Y.%m.%d')}] {log[1]}" for log in prev_week_work_logs])
else:
   previous_week_summary = "No logs found for the previous week."

# 금주업무 내역 조합
if this_week_logs:
   this_week_summary = "\n".join([f"[{log[0].strftime('%Y.%m.%d')}] {log[1]}" for log in this_week_logs])
else:
   this_week_summary = ""

# Pre-fill form fields
previous_week = st.text_area("전주업무", value=previous_week_summary, height=150)
this_week = st.text_area("금주업무", value=this_week_summary, height=150)
remarks = st.text_area("비고", height=100)

# Save data to Google Sheets and MySQL
if st.button("Save to Google Sheets and MySQL"):
   # Convert date for database and sheets
   registered_date_str = 등록일.strftime('%Y.%m.%d')
   registered_date_for_db = datetime.combine(등록일, datetime.min.time())

   # Create a new row for Google Sheets
   new_row = [registered_date_str, task_type, worker, previous_week, this_week, remarks]

   # Update or insert in Google Sheets
   sheet_data = sheet.get_all_values()
   df_sheet = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])
   matching_rows = df_sheet[
       (df_sheet['등록일'] == registered_date_str) &
       (df_sheet['업무유형'] == task_type) &
       (df_sheet['작업자'] == worker)
   ]

   if not matching_rows.empty:
       # Update existing row
       row_index = matching_rows.index[0] + 2
       sheet.update(f'A{row_index}:F{row_index}', [new_row])
       st.success("Updated weekly journal in Google Sheets!")
   else:
       # Append new row
       sheet.append_row(new_row)
       st.success("Added new weekly journal entry to Google Sheets!")

   # Update or insert in MySQL
   cursor.execute("""
       SELECT id FROM weekly_journal 
       WHERE DATE(등록일) = %s AND 업무유형 = %s AND 작업자 = %s
   """, (registered_date_for_db, task_type, worker))
   existing_entry = cursor.fetchone()

   if existing_entry:
       cursor.execute("""
           UPDATE weekly_journal 
           SET 전주업무 = %s, 금주업무 = %s, 비고 = %s 
           WHERE id = %s
       """, (previous_week, this_week, remarks, existing_entry[0]))
       st.success("Updated weekly journal in MySQL!")
   else:
       cursor.execute("""
           INSERT INTO weekly_journal (등록일, 업무유형, 작업자, 전주업무, 금주업무, 비고) 
           VALUES (%s, %s, %s, %s, %s, %s)
       """, (registered_date_for_db, task_type, worker, previous_week, this_week, remarks))
       st.success("Added new weekly journal entry to MySQL!")

# Display updated Google Sheets data
updated_sheet_data = sheet.get_all_values()
updated_df = pd.DataFrame(updated_sheet_data[1:], columns=updated_sheet_data[0])
st.dataframe(updated_df)

# Close MySQL connection
cursor.close()
conn.close()