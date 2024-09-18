import streamlit as st
import time
import bcrypt
import pybase64
import urllib.parse
import requests
import datetime
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from konlpy.tag import Okt
from collections import Counter
import re

import os
from dotenv import load_dotenv
load_dotenv()

# Account Information

smartstore_client_id = os.getenv('SMARTSTORE_CLIENT_ID')
smartstore_client_secret = os.getenv('SMARTSTORE_CLIENT_SECRET')


st.write("# 네이버 스마트 스토어! 👋")


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


params_answered = True

params_interval = st.slider("검색 데이터 일수",min_value=5,max_value=60,step=1,value=10)# 오늘부터 며칠 전까지?
params_display = st.slider("보여줄 데이터 수", min_value=1,max_value=10,step=1,value=5)
params_bulletin = st.selectbox("게시판 유형",("Q&A","1:1"))

answered = st.selectbox("답변 완료 유무",("답변 완료", "새 질문"))
if answered == "새 질문":
    params_answered = False
if params_bulletin == "Q&A":
    # 현재 날짜 및 시간 구하기
    current_datetime = datetime.datetime.now()
    print(current_datetime)
    # toDate값 설정 (현재 날짜 및 시간)
    to_date = current_datetime.strftime('%Y-%m-%dT%H:%M:%S.100+09:00')
    print(to_date)
    #to_date = current_datetime.strftime('%Y-%m-%dT%H:%M:%S')
    # fromDate값 계산 (toDate값으로부터 7일 이전)
    from_date = (current_datetime - datetime.timedelta(days=params_interval)).strftime('%Y-%m-%dT%H:%M:%S.100+09:00')
    #from_date = (current_datetime - datetime.timedelta(days=interval)).strftime('%Y-%m-%dT%H:%M:%S')
    # 요청할 URL의 기본 부분
    base_url = "https://api.commerce.naver.com/external/v1/contents/qnas"


    # 쿼리 파라미터 설정
    query_params = {
        'page': 1,
        'size': 100,
     #   'answered': params_answered,
        'fromDate': from_date,
        'toDate': to_date
    }

    # 헤더 설정
    headers = { 'Authorization': f"Bearer {st_access_token}" }

    # GET 요청 보내기
    response = requests.get(base_url, params=query_params, headers=headers)

    articles_data = []
    new_articles_data=[]
    # 응답 처리
    if response.status_code == 200:
        data = response.json()
        for qna in data['contents']:
            if qna['answered']==1:
                createDate = qna['createDate']
                question = qna['question']
                answer = qna['answer']
                articles_data.append({'date': createDate,'question':question,'answer':answer})

            elif qna['answered']==0:
                createDate = qna['createDate']
                question = qna['question']
                answer = "답변 필요"
                new_articles_data.append({'date': createDate,'question':question,'answer': answer})

    else:
        print("Error:", response.text)
    if answered != "새 질문":
        df = pd.DataFrame(articles_data)
        st.table(df.head(params_display))
    else:
        df = pd.DataFrame(new_articles_data)
        st.table(df.head(params_display))

    

else:
    # Define the interval in days
    interval = 300

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
        'size': 100,
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
    new_articles_data = []
    # Process the response
    if response.status_code == 200:
        data = response.json()
        for qna in data['content']:
            createDate = qna['inquiryRegistrationDateTime']
            question = qna['inquiryContent']
            if qna['answered'] == 1:
                answer = qna['answerContent']
                articles_data.append({'date': createDate,'question':question,'answer':answer})
            else:
                answer = "답변 필요"
                new_articles_data.append({'date': createDate, 'question': question, 'answer': answer})
    else:
        print("Error:", response.text)

    if answered != "새 질문":
        df = pd.DataFrame(articles_data)
        st.table(df.head(params_display))
    else:
        df = pd.DataFrame(new_articles_data)
        st.table(df.head(params_display))


if params_bulletin == "Q&A":
    articles_data = []
    new_articles_data = []
    if response.status_code == 200:
        data = response.json()
        for qna in data['contents']:
            createDate = qna['createDate']
            question = qna['question']
            if qna['answered'] == 1:
                answer = qna['answer']
                # Append both question and answer to the articles_data list
                articles_data.append({'date': createDate, 'text': question + " " + answer})
            else:
                # If there's no answer, treat it as question only
                new_articles_data.append({'date': createDate, 'text': question})
    else:
        print("Error:", response.text)

else:
    # Initialize a list to store the data
    articles_data = []
    new_articles_data = []

    # Process the response
    if response.status_code == 200:
        data = response.json()
        for qna in data['content']:
            createDate = qna['inquiryRegistrationDateTime']
            question = qna['inquiryContent']
            if qna['answered'] == 1:
                answer = qna['answerContent']
                articles_data.append({'date': createDate,'text': question + " " + answer})
            else:
                answer = "답변 필요"
                new_articles_data.append({'date': createDate, 'text': question})
    else:
        print("Error:", response.text)

if answered  != "새 질문":
    df = pd.DataFrame(articles_data)
else:
    df = pd.DataFrame(new_articles_data)

# Define the list of Korean device names to analyze
korean_device_names_to_analyze = ['허브', '센서', '플러그', '콘센트', '조명스위치', '블라인드', '커튼', '카메라', '도어락','온습도','조도','누수','스위치','무선 스위치']

# Extract Korean device names from the text using regular expressions
korean_device_names = []
if len(df)!=0:

    for text in df['text']:
        for device in korean_device_names_to_analyze:
            matches = re.findall(r'\b{}\b'.format(device), text)
            korean_device_names.extend(matches)

# Count occurrences of each Korean device name
korean_word_count = Counter(korean_device_names)

# Generate the word cloud
if len(korean_word_count)!=0:
    korean_wordcloud = WordCloud(
        font_path='/System/Library/Fonts/AppleSDGothicNeo.ttc',  # 한글 폰트 경로
        background_color='white',
        width=800,
        height=600
    ).generate_from_frequencies(korean_word_count)

    # 한글 폰트 설정
    plt.rcParams['font.family'] = 'AppleGothic'  # Mac의 경우 AppleGothic, Windows의 경우 Malgun Gothic 등을 사용합니다.

    # 빈도수가 높은 순으로 정렬된 튜플 리스트 생성
    sorted_korean_word_count = korean_word_count.most_common()

    # 정렬된 데이터를 사용하여 막대 그래프 생성
    fig, ax = plt.subplots(figsize=(10, 8))
    words, counts = zip(*sorted_korean_word_count)  # 단어와 빈도수를 분리
    ax.bar(words, counts, color='skyblue')
    ax.set_xlabel('단어')
    ax.set_ylabel('빈도')
    ax.set_title('한글 단어 빈도 (빈도수 기준 정렬)')
    plt.xticks(rotation=45)

    # Streamlit에서 사용할 수 있도록 이미지를 Base64로 인코딩하여 표시
    st.write("### 관심 디바이스 키워드 수")
    st.pyplot(fig)
    st.write("### 관심 디바이스 워드 클라우드")
    # Visualize the word cloud
    st.image(korean_wordcloud.to_array(), use_column_width=True)

