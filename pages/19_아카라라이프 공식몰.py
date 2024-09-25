import streamlit as st
import requests
import base64
import requests
import re
import datetime
from bs4 import BeautifulSoup
import os
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

cafe24_mall_id = os.getenv('CAFE24_MALL_ID')
cafe24_client_id = os.getenv('CAFE24_CLIENT_ID')
cafe24_client_secret = os.getenv('CAFE24_CLIENT_SECRET')


st.write("# 아카라라이프 자사몰! 👋")


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






params_interval= st.slider("검색 데이터 일수",min_value=5,max_value=30,step=1,value=10)# 오늘부터 며칠 전까지?
params_display = st.slider("보여줄 데이터 수", min_value=1,max_value=10,step=1,value=5)
params_bulletin = st.selectbox("게시판 유형",("Q&A","1:1","상품평"))
bulletin= 6
if params_bulletin=="1:1":
    bulletin = 9
elif params_bulletin=="상품평":
    bulletin = 4
    
payload = {}
files = {}
headers = {
    'Authorization': f'Bearer {access_token}',
    'X-Cafe24-Api-Version': '2024-03-01',
    'Content-Type': 'application/json',
    'Cookie': 'ECSESSID=5d169e847b0b49d2ff41047129114582'
}

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

response = requests.request("GET", url, headers=headers, data=payload, files=files,params=params)
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
st.table(df.head(params_display))


# Define the list of Korean device names to analyze
korean_device_names_to_analyze = ['M2','E1','허브', '센서', '플러그', '콘센트', '조명스위치', '블라인드', '커튼', '카메라', '도어락','온습도','조도','누수','스위치','무선 스위치','스마트 플러그','플러그']

# Extract Korean device names from the text using regular expressions
korean_device_names = []
if len(df)!=0:

    for text in df['contents']:
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
    print(sorted_korean_word_count)
    print(df['contents'])

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

