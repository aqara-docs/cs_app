import streamlit as st
import requests
import base64
import requests
import re
import datetime
#from datetime import timedelta
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse
import bcrypt
import pybase64
import time
import optparse

import os
from dotenv import load_dotenv
load_dotenv()

# Account Information

cafe24_mall_id = os.getenv('CAFE24_MALL_ID')
cafe24_client_id = os.getenv('CAFE24_CLIENT_ID')
cafe24_client_secret = os.getenv('CAFE24_CLIENT_SECRET')

smartstore_client_id = os.getenv('SMARTSTORE_CLIENT_ID')
smartstore_client_secret = os.getenv('SMARTSTORE_CLIENT_SECRET')

channeltalk_access_key = os.getenv('CHANNELTALK_ACCESS_KEY')
channeltalk_access_secret = os.getenv('CHANNELTALK_ACCESS_SECRET')

st.write("# 답변해 주세요!!!")

st.write("### 아카라라이프 자사몰 👋")


# 기본 인증 정보 생성
basic_auth = f"{cafe24_client_id}:{cafe24_client_secret}"
encoded_basic_auth = base64.b64encode(basic_auth.encode()).decode()

# 요청 URL 설정
url = f"https://{cafe24_mall_id}.cafe24api.com/api/v2/oauth/token"
headers = {
    'Authorization': f"Basic {encoded_basic_auth}",
    'Content-Type': 'application/x-www-form-urlencoded'
}

# refresh.csv 파일에서 refresh token 값을 읽어옴
#with open('./refresh.csv', 'r') as file:
#    refresh_token = file.read().strip()



file_path = './pages/refresh.csv'
if os.path.isfile(file_path):
    print(file_path)
    with open(file_path, 'r') as file:
        refresh_token = file.read().strip()
else:
    print(f"File not found: {file_path}")



# 요청 데이터 설정
data = {
    'grant_type': 'refresh_token',
    'refresh_token': refresh_token
}

# POST 요청 보내기
response = requests.post(url, headers=headers, data=data)

# access_token 및 refresh_token 값 읽어오기
if response.status_code == 200:
    response_data = response.json()
    access_token = response_data['access_token']
    refresh_token = response_data['refresh_token']
    print("Access Token:", access_token)
    print("Refresh Token:", refresh_token)
    print(response.json())
    # refresh token을 CSV 파일에 저장
    with open(file_path, 'w') as file:
        file.write(refresh_token)
else:
    print("Error:", response.text)

st.write("#### 게시판")

bulletin = 6
url = f"https://aqarakr.cafe24api.com/api/v2/admin/boards/{bulletin}/articles"

interval = 60 # 오늘부터 며칠 전까지?
payload = {}
files = {}
headers = {
    'Authorization': f'Bearer {access_token}',
    'X-Cafe24-Api-Version': '2024-03-01',
    'Content-Type': 'application/json',
    'Cookie': 'ECSESSID=5d169e847b0b49d2ff41047129114582'
}

# 현재 날짜를 가져옵니다.
current_date = datetime.datetime.now()

# end_date로부터 7일 전의 날짜를 구합니다.
start_date = current_date - datetime.timedelta(days=interval)

# 날짜를 원하는 형식으로 포맷팅합니다.
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = current_date.strftime('%Y-%m-%d')

params = {
    'start_date': start_date_str,
    'end_date': end_date_str
}

response = requests.request("GET", url, headers=headers, data=payload, files=files, params=params)
data = response.json()
#print(data)
articles_data = []
for article in data['articles']:
    # 각 기사의 날짜 가져오기
    article_date = article['created_date']
    # 해당 날짜의 기사 내용 가져오기
    content = article['content']
    status = article['reply_sequence']
    text = BeautifulSoup(content, "html.parser").get_text()
    if (article['member_id'] != 'aqaralifecs') and status==1:
      articles_data.append({'date': article_date, 'text': text,'status':status})
#      print("hi")
    #print(f"Date: {article_date}")
    #print(text)
if len(articles_data)==0:
  df = pd.DataFrame()
  st.write("모두 답변하였습니다!!!")
else:
  df = pd.DataFrame(articles_data)
  st.table(df.loc[:,['date','text']].head(10))

st.write("#### 1:1 문의")
bulletin = 9
url = f"https://aqarakr.cafe24api.com/api/v2/admin/boards/{bulletin}/articles"

interval = 60 # 오늘부터 며칠 전까지?
payload = {}
files = {}
headers = {
    'Authorization': f'Bearer {access_token}',
    'X-Cafe24-Api-Version': '2024-03-01',
    'Content-Type': 'application/json',
    'Cookie': 'ECSESSID=5d169e847b0b49d2ff41047129114582'
}

# 현재 날짜를 가져옵니다.
current_date = datetime.datetime.now()

# end_date로부터 7일 전의 날짜를 구합니다.
start_date = current_date - datetime.timedelta(days=interval)

# 날짜를 원하는 형식으로 포맷팅합니다.
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = current_date.strftime('%Y-%m-%d')

params = {
    'start_date': start_date_str,
    'end_date': end_date_str
}

response = requests.request("GET", url, headers=headers, data=payload, files=files, params=params)
data = response.json()
#print(data)
articles_data = []
for article in data['articles']:
    # 각 기사의 날짜 가져오기
    article_date = article['created_date']
    # 해당 날짜의 기사 내용 가져오기
    content = article['content']
    status = article['reply_sequence']
    text = BeautifulSoup(content, "html.parser").get_text()
    if (article['member_id'] != 'aqaralifecs') and status==1:
      articles_data.append({'date': article_date, 'text': text,'status':status})
#      print("hi")
    #print(f"Date: {article_date}")
    #print(text)
if len(articles_data)==0:
  df = pd.DataFrame()
  st.write("모두 답변하였습니다!!!")
else:
  df = pd.DataFrame(articles_data)
  st.table(df.loc[:,['date','text']].head(10))

st.write("#### 금일 상품평")
st.write("참고 - 금일 상품평은 답변 유무는 알 수 없으며 금일 상품평만을 보여 줍니다.")
bulletin = 4
url = f"https://aqarakr.cafe24api.com/api/v2/admin/boards/{bulletin}/articles"

interval = 0 # 오늘부터 며칠 전까지?
payload = {}
files = {}
headers = {
    'Authorization': f'Bearer {access_token}',
    'X-Cafe24-Api-Version': '2024-03-01',
    'Content-Type': 'application/json',
    'Cookie': 'ECSESSID=5d169e847b0b49d2ff41047129114582'
}

# 현재 날짜를 가져옵니다.
current_date = datetime.datetime.now()

# end_date로부터 7일 전의 날짜를 구합니다.
start_date = current_date - datetime.timedelta(days=interval)

# 날짜를 원하는 형식으로 포맷팅합니다.
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = current_date.strftime('%Y-%m-%d')

params = {
    'start_date': start_date_str,
    'end_date': end_date_str
}

response = requests.request("GET", url, headers=headers, data=payload, files=files, params=params)
data = response.json()
print(data)
articles_data = []
for article in data['articles']:
    # 각 기사의 날짜 가져오기
    article_date = article['created_date']
    # 해당 날짜의 기사 내용 가져오기
    content = article['content']
    status = article['reply_sequence']
    text = BeautifulSoup(content, "html.parser").get_text()
    if (article['member_id'] != 'aqaralifecs') and status==1:
      articles_data.append({'date': article_date, 'text': text,'status':status})
#      print("hi")
    #print(f"Date: {article_date}")
    #print(text)
if len(articles_data)==0:
  df = pd.DataFrame()
  st.write("금일 작성된 새로운 상품평은 없습니다 !!!")
else:
  df = pd.DataFrame(articles_data)
  st.table(df.loc[:,['date','text']].head(20))


###########################
##### 네이버 스마트 스토어 #####

st.write("### 네이버 스마트 스토어 👋")

def get_token(client_id, client_secret):
    try:
        timestamp = str(int((time.time() - 3) * 1000))
        pwd = f'{client_id}_{timestamp}'
        hashed = bcrypt.hashpw(pwd.encode('utf-8'), client_secret.encode('utf-8'))
        client_secret_sign = pybase64.standard_b64encode(hashed).decode('utf-8')

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data_ = {
            "client_id": client_id,
            "timestamp": timestamp,
            "grant_type": "client_credentials",
            "client_secret_sign": client_secret_sign,
            "type": "SELF"
        }
        
    #    if type_ != "SELF":
     #       data_["type"] = type_

        # Encode data_ dictionary into a URL-encoded string
        body = urllib.parse.urlencode(data_)

        url = 'https://api.commerce.naver.com/external/v1/oauth2/token'
        print("Request URL:", url)
        print("Request Body:", body)

        res = requests.post(url=url, headers=headers, data=body)
        res.raise_for_status()  # Raise an exception for HTTP errors

        res_data = res.json()
        if 'access_token' in res_data:
            return res_data['access_token']
        else:
            raise ValueError(f'Token request failed: {res_data}')
    
    except Exception as e:
        print(f'Error occurred: {e}')
        return None

st_access_token = get_token(client_id=smartstore_client_id, client_secret=smartstore_client_secret)
if st_access_token:
    print(f'Issued token: {st_access_token}')
else:
    print('Failed to obtain token.')

interval=5
# 현재 날짜 및 시간 구하기
current_datetime = datetime.datetime.now()
#print(current_datetime)
# toDate값 설정 (현재 날짜 및 시간)
to_date = current_datetime.strftime('%Y-%m-%dT%H:%M:%S.100+09:00')
#print(to_date)
#to_date = current_datetime.strftime('%Y-%m-%dT%H:%M:%S')
# fromDate값 계산 (toDate값으로부터 7일 이전)
from_date = (current_datetime - datetime.timedelta(days=interval)).strftime('%Y-%m-%dT%H:%M:%S.100+09:00')
#from_date = (current_datetime - datetime.timedelta(days=interval)).strftime('%Y-%m-%dT%H:%M:%S')
# 요청할 URL의 기본 부분
base_url_naver = "https://api.commerce.naver.com/external/v1/contents/qnas"

# 쿼리 파라미터 설정
query_params = {
    'page': 1,
    'size': 10,
   # 'answered': 0,
    'fromDate': from_date,
    'toDate': to_date
}

# 헤더 설정
headers = { 'Authorization': f"Bearer {st_access_token}" }

# GET 요청 보내기
response = requests.request("GET",base_url_naver, params=query_params, headers=headers)

naver_data = []
naver_data1 = []
# 응답 처리
if response.status_code == 200:
    data = response.json()
    print("##########################")
    for qna in data['contents']:
        if qna['answered']==1:
          createDate = qna['createDate']
          question = qna['question']
          answer = qna['answer']
          #print(f"CreateDate: {createDate}")
          #print(f"Question: {question}")
          #print(f"Answer: {answer}")
          #print()
          naver_data.append({'date': createDate,'question':question,'answer':answer})
        elif qna['answered']==0:
          createDate = qna['createDate']
          question = qna['question']
          print("hmmm~~~~")
          #answer = qna['answer']
          #print(f"CreateDate: {createDate}")
          #print(f"Question: {question}")
          #print(f"Answer: {answer}")
          naver_data1.append({'date': createDate,'question':question})

          print()
else:
    print("Error:", response.text)
st.write("#### 게시판")

print((naver_data1))
if len(naver_data1)==0:
   st.write("모두 답변했습니다 !!!")
else:
   df = pd.DataFrame(naver_data1)
   print("there~~~~~~")
   st.table(df.loc[:,['date','question']].head(10))

st.write("#### 1:1 문의")

# Define the interval in days
interval = 10

# Get the current date and time
current_datetime = datetime.datetime.now()

# Set to_date to the current date in the correct format
to_date = current_datetime.strftime('%Y-%m-%d')

# Calculate from_date as to_date minus the interval in days, also in the correct format
from_date = (current_datetime - datetime.timedelta(days=interval)).strftime('%Y-%m-%d')

# Base URL for the request
base_url = "https://api.commerce.naver.com/external/v1/pay-user/inquiries"

# Query parameters
query_params = {
    'page': 1,
    'size': 10,
    'startSearchDate': from_date,
    'endSearchDate': to_date
}

# Replace with your actual access token
#st_access_token = 'YOUR_ACCESS_TOKEN_HERE'

# Headers
headers = { 'Authorization': f"Bearer {st_access_token}" }

# Send the GET request
response = requests.request("GET",base_url, params=query_params, headers=headers)
#print(response.text)
# Initialize a list to store the data
articles_data = []

# Process the response
if response.status_code == 200:
    data = response.json()
    for qna in data['content']:
        createDate = qna['inquiryRegistrationDateTime']
        question = qna['inquiryContent']
        if qna['answered'] == 1:
            answer = qna['answerContent']
        else:
            answer = "답변 필요"
            articles_data.append({'date': createDate, 'question': question, 'answer': answer})
else:
    print("Error:", response.text)

if len(articles_data)==0:
   st.write("모두 답변했습니다!!!")
else:
   df = pd.DataFrame(articles_data)
   st.table(df.loc[df['answer']=="답변 필요", ['date','question']].head(10))




st.write("### 채널톡 👋")



# 어제와 오늘의 날짜 구하기
yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
today = datetime.datetime.now()

# API 엔드포인트 및 인증 정보
url = "https://api.channel.io/open/v5/user-chats"
headers = {
    "accept": "application/json",
    "x-access-key": f"{channeltalk_access_key}",
    "x-access-secret": f"{channeltalk_access_secret}"
}
params = {
    "state": "opened",
    "sortOrder": "desc",
    "limit": 100,
    "from": int(yesterday.timestamp() * 1000),  # 어제 자정부터
    "to": int(today.timestamp() * 1000)  # 현재까지
}

# API 요청 보내기
response = requests.get(url, headers=headers, params=params)

# 응답 확인
if response.status_code == 200:
    chats = response.json().get("messages", [])
    #print(chats)
    df = pd.DataFrame(chats)
    df = df[['personType','plainText', 'updatedAt', 'createdAt']].rename(columns={'plainText': 'text'})
    df = df[df['text'].str.strip() != '']
    # updatedAt과 createdAt의 timestamp 값을 datetime 형식으로 변환
    df['updatedAt'] = pd.to_datetime(df['updatedAt'], unit='ms') + pd.Timedelta(hours=9)
    df['createdAt'] = pd.to_datetime(df['createdAt'], unit='ms') + pd.Timedelta(hours=9)
    df_sorted = df.loc[df['personType']=="user", ['updatedAt', 'text','personType']].sort_values(by='updatedAt', ascending=False)
    st.table(df_sorted.loc[:,['updatedAt','text']].dropna().head(20))
else:
    print("API 요청에 실패하였습니다.")