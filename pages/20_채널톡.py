import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from konlpy.tag import Okt
from collections import Counter
import re


import os
from dotenv import load_dotenv
load_dotenv()

# Account Information

channeltalk_access_key = os.getenv('CHANNELTALK_ACCESS_KEY')
channeltalk_access_secret = os.getenv('CHANNELTALK_ACCESS_SECRET')

st.write("# 채널톡! 👋")


# 어제와 오늘의 날짜 구하기
yesterday = datetime.now() - timedelta(days=1)
today = datetime.now()

# API 엔드포인트 및 인증 정보
url = "https://api.channel.io/open/v5/user-chats"
headers = {
    "accept": "application/json",
    "x-access-key": f"{channeltalk_access_key}",
    "x-access-secret": f"{channeltalk_access_secret}"
}

#params_sort = st.selectbox("정렬",("desc","asc"))
params_sort = "desc"
params_limit = st.slider("검색 데이터 수",min_value=20,max_value=500,step=20,value=100)
params_display = st.slider("보여줄 데이터 수", min_value=1,max_value=10,step=1,value=5)
params_state_temp = st.selectbox("고객 지원 완료 여부",("새질문 또는 답변 중","답변 완료"))
if params_state_temp == "답변 완료":
    params_state = "closed"
else:
    params_state = "opened"
params = {
    "state": params_state,
    "sortOrder": params_sort,
    "limit": params_limit,
    "from": int(yesterday.timestamp() * 1000),  # 어제 자정부터
    "to": int(today.timestamp() * 1000)  # 현재까지
}

if params_sort == "desc":
    sort_status= False
else:
    sort_status= True
# API 요청 보내기
response = requests.get(url, headers=headers, params=params)

# 응답 확인
if response.status_code == 200:
    chats = response.json().get("messages", [])
    df = pd.DataFrame(chats)
    df = df[['plainText', 'updatedAt', 'createdAt']].rename(columns={'plainText': 'text'})
    df = df[df['text'].str.strip() != '']
    # updatedAt과 createdAt의 timestamp 값을 datetime 형식으로 변환
    df['updatedAt'] = pd.to_datetime(df['updatedAt'], unit='ms') + pd.Timedelta(hours=9)
    df['createdAt'] = pd.to_datetime(df['createdAt'], unit='ms') + pd.Timedelta(hours=9)
    df_sorted = df.loc[:, ['updatedAt', 'text']].sort_values(by='updatedAt', ascending=sort_status)
    st.table(df_sorted.dropna().head(params_display))
else:
    print("API 요청에 실패하였습니다.")

# Define the list of Korean device names to analyze
korean_device_names_to_analyze = ['허브', '센서', '플러그', '콘센트', '조명스위치', '블라인드', '커튼', '카메라', '도어락','온습도','조도','누수','스위치','무선 스위치']

# Extract Korean device names from the text using regular expressions
korean_device_names = []
if len(df_sorted.dropna())!=0:

    for text in df_sorted.dropna()['text']:
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

