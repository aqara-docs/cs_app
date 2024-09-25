import streamlit as st
import requests
import base64
import re
import datetime
from bs4 import BeautifulSoup
import os
import pandas as pd
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

# Account Information
cafe24_mall_id = os.getenv('CAFE24_MALL_ID')
cafe24_client_id = os.getenv('CAFE24_CLIENT_ID')
cafe24_client_secret = os.getenv('CAFE24_CLIENT_SECRET')

st.write("# 아카라라이프 자사몰! 👋")

# Basic Auth Setup
basic_auth = f"{cafe24_client_id}:{cafe24_client_secret}"
encoded_basic_auth = base64.b64encode(basic_auth.encode()).decode()

# URL for request
url = f"https://{cafe24_mall_id}.cafe24api.com/api/v2/oauth/token"
headers = {
    'Authorization': f"Basic {encoded_basic_auth}",
    'Content-Type': 'application/x-www-form-urlencoded'
}

# Read refresh token from file
file_path = './pages/refresh.csv'
if os.path.isfile(file_path):
    with open(file_path, 'r') as file:
        refresh_token = file.read().strip()

# Request data for token refresh
data = {
    'grant_type': 'refresh_token',
    'refresh_token': refresh_token
}

# Send POST request for access token
response = requests.post(url, headers=headers, data=data)

# Handle response
if response.status_code == 200:
    response_data = response.json()
    access_token = response_data['access_token']
    refresh_token = response_data['refresh_token']
    with open(file_path, 'w') as file:
        file.write(refresh_token)

params_interval = st.slider("검색 데이터 일수", min_value=5, max_value=50, step=1, value=60)
params_display = st.slider("보여줄 데이터 수", min_value=1, max_value=10, step=1, value=5)

bulletin = 6
headers = {
    'Authorization': f'Bearer {access_token}',
    'X-Cafe24-Api-Version': '2024-03-01',
    'Content-Type': 'application/json'
}

url = f"https://aqarakr.cafe24api.com/api/v2/admin/boards/{bulletin}/articles"

# Date calculations
current_date = datetime.datetime.now()
start_date = current_date - datetime.timedelta(days=params_interval)

start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = current_date.strftime('%Y-%m-%d')

params = {
    'start_date': start_date_str,
    'end_date': end_date_str,
    'limit': 100
}

response = requests.request("GET", url, headers=headers, params=params)
data = response.json()

articles_data = []
for article in data['articles']:
    article_date = article['created_date']
    content = article['content']
    status = article['reply_sequence']
    filtered_text = BeautifulSoup(content, "html.parser").get_text()
    articles_data.append({'registered_date': article_date, 'contents': filtered_text, 'writer': article['writer']})

df = pd.DataFrame(articles_data)

# Combine odd and even rows
combined_rows = []
for i in range(0, len(df), 2):
    if i + 1 < len(df):
        combined_content = df.iloc[i + 1]['writer'] + ": " + df.iloc[i + 1]['contents']
        
        question = ""
        answer = ""
        if "[ Original Message ]" in combined_content:
            parts = combined_content.split("[ Original Message ]")
            if len(parts) > 1:
                question = parts[1].strip()
        if "아카라라이프CS:" in combined_content:
            answer_parts = combined_content.split("아카라라이프CS:")
            if len(answer_parts) > 1:
                answer = answer_parts[1].strip()

        combined_rows.append({
            'registered_date': df.iloc[i]['registered_date'],  
            'question': question,  
            'answer': answer  
        })

combined_df = pd.DataFrame(combined_rows)

st.subheader("Q&A 게시판")
st.table(combined_df.head(params_display))

# MySQL Connection Setup
conn = mysql.connector.connect(
    user=os.getenv('SQL_USER'),
    password=os.getenv('SQL_PASSWORD'),
    host=os.getenv('SQL_HOST'),
    database=os.getenv('SQL_DATABASE'),
    charset='utf8mb4',
    collation='utf8mb4_general_ci'
)

conn.autocommit = True
cursor = conn.cursor()

# Query for insert or update
query = """
INSERT INTO cafe24_qna (
    registered_date, question, answer
) VALUES (
    %s, %s, %s
) ON DUPLICATE KEY UPDATE
    answer = VALUES(answer);
"""

# Function to insert or update Q&A
def insert_or_update_qna(df):
    try:
        for index, row in df.iterrows():
            # Parse date string to datetime object
            if isinstance(row['registered_date'], str):
                date_obj = datetime.datetime.strptime(row['registered_date'], '%Y-%m-%dT%H:%M:%S+09:00')
            else:
                date_obj = row['registered_date']

            formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S') if date_obj else None

            values = [
                formatted_date,
                row['question'] if row['question'] else None,
                row['answer'] if row['answer'] else None
            ]
            cursor.execute(query, values)
        
        conn.commit()
        st.write("Data has been successfully saved or updated in MySQL.")
    except Error as e:
        st.write(f"Error while connecting to MySQL: {e}")
    finally:
        cursor.close()
        conn.close()

# Insert or update Q&A in MySQL
insert_or_update_qna(combined_df)

# You can repeat the process for other types of data (1:1, product reviews, etc.) following a similar pattern.


bulletin = 9
url = f"https://aqarakr.cafe24api.com/api/v2/admin/boards/{bulletin}/articles"
# 현재 날짜를 가져옵니다.
current_date = datetime.datetime.now()

# end_date로부터 7일 전의 날짜를 구합니다.
start_date = current_date - datetime.timedelta(days=params_interval)

# 날짜를 원하는 형식으로 포맷팅합니다.
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = current_date.strftime('%Y-%m-%d')

current_date = datetime.datetime.now().strftime('%Y-%m-%d')

params = {
    'start_date': start_date_str,
    'end_date': end_date_str,
    'limit':100
}

response = requests.request("GET", url, headers=headers,params=params)
data = response.json()
articles_data = []
for article in data['articles']:
    # 각 기사의 날짜 가져오기
    article_date = article['created_date']
    # 해당 날짜의 기사 내용 가져오기
    content = article['content']
    filtered_text = BeautifulSoup(content, "html.parser").get_text()
    #st.write(f"Date: {article_date}")
    #st.write(filtered_text)
    articles_data.append({'registered_date': article_date, 'contents': filtered_text,'writer': article['writer']})


df = pd.DataFrame(articles_data)
# 홀수행과 짝수행을 하나로 합치는 작업 (1:1 게시판 버전)
combined_rows_1to1 = []
for i in range(0, len(df), 2):
    if i + 1 < len(df):
        answer = df.iloc[i + 1]['writer'] + ": " + df.iloc[i + 1]['contents']
        question = df.iloc[i]['writer'] + ": " + df.iloc[i]['contents']

        combined_rows_1to1.append({
            'registered_date': df.iloc[i]['registered_date'],  # 홀수행의 registered_date 유지
            'question': question,  # 짝수행의 writer와 contents 결합
            'answer': answer  # 홀수행의 writer와 contents 결합
        })

# 합쳐진 데이터를 새로운 DataFrame으로 생성
combined_df_1to1 = pd.DataFrame(combined_rows_1to1)

# 삭제된 writer 칼럼 없이 출력
st.subheader("1:1 게시판")
st.table(combined_df_1to1.head(params_display))
# Autocommit 활성화
# MySQL Connection Setup
conn = mysql.connector.connect(
    user=os.getenv('SQL_USER'),
    password=os.getenv('SQL_PASSWORD'),
    host=os.getenv('SQL_HOST'),
    database=os.getenv('SQL_DATABASE'),
    charset='utf8mb4',
    collation='utf8mb4_general_ci'
)

conn.autocommit = True
cursor = conn.cursor()

# Insert or Update query
query = """
INSERT INTO cafe24_1to1 (
    registered_date, question, answer
) VALUES (
    %s, %s, %s
) ON DUPLICATE KEY UPDATE
    answer = VALUES(answer);
"""


# MySQL에 데이터 삽입/업데이트
def insert_or_update_1to1(df):
    try:
        for index, row in df.iterrows():
            # 상품명, 상품옵션, 배송메시지, 특이사항을 None으로 변경
            if isinstance(row['registered_date'], str):
                date_obj = datetime.datetime.strptime(row['registered_date'], '%Y-%m-%dT%H:%M:%S+09:00')
            else:
                date_obj = row['registered_date']

            formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S') if date_obj else None
            # Check if 'question' and 'answer' columns exist in the row
            

            values = [
                formatted_date,
                row['question'] if row['question'] else None,
                row['answer'] if row['answer'] else None
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
insert_or_update_1to1(combined_df_1to1)



bulletin = 4
url = f"https://aqarakr.cafe24api.com/api/v2/admin/boards/{bulletin}/articles"
# 현재 날짜를 가져옵니다.
current_date = datetime.datetime.now()

# end_date로부터 7일 전의 날짜를 구합니다.
start_date = current_date - datetime.timedelta(days=params_interval)

# 날짜를 원하는 형식으로 포맷팅합니다.
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = current_date.strftime('%Y-%m-%d')

current_date = datetime.datetime.now().strftime('%Y-%m-%d')

params = {
    'start_date': start_date_str,
    'end_date': end_date_str,
    'limit':100
}

response = requests.request("GET", url, headers=headers,params=params)
data = response.json()
articles_data = []
for article in data['articles']:
    # 각 기사의 날짜 가져오기
    article_date = article['created_date']
    # 해당 날짜의 기사 내용 가져오기
    content = article['content']
    filtered_text = BeautifulSoup(content, "html.parser").get_text()
    #st.write(f"Date: {article_date}")
    #st.write(filtered_text)
    articles_data.append({'registered_date': article_date, 'contents': filtered_text,'writer': article['writer']})



# 삭제된 writer 칼럼 없이 출력
st.subheader("상품평")
df = pd.DataFrame(articles_data)
st.table(df.head(params_display))

# MySQL Connection Setup
conn = mysql.connector.connect(
    user=os.getenv('SQL_USER'),
    password=os.getenv('SQL_PASSWORD'),
    host=os.getenv('SQL_HOST'),
    database=os.getenv('SQL_DATABASE'),
    charset='utf8mb4',
    collation='utf8mb4_general_ci'
)

conn.autocommit = True
cursor = conn.cursor()

# Insert or Update query
query = """
INSERT INTO cafe24_review (
    registered_date, contents, writer
) VALUES (
    %s, %s, %s
) ON DUPLICATE KEY UPDATE
    writer = VALUES(writer);
"""


# MySQL에 데이터 삽입/업데이트
def insert_or_update_review(df):
    try:
        for index, row in df.iterrows():
            # 상품명, 상품옵션, 배송메시지, 특이사항을 None으로 변경
            if isinstance(row['registered_date'], str):
                date_obj = datetime.datetime.strptime(row['registered_date'], '%Y-%m-%dT%H:%M:%S+09:00')
            else:
                date_obj = row['registered_date']

            formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S') if date_obj else None

            values = [
                formatted_date,
                row['contents'] if row['contents'] else None,
                row['writer'] if row['writer'] else None
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
insert_or_update_review(df)