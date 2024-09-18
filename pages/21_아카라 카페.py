import streamlit as st
import time
from selenium import webdriver
import csv
import pandas as pd
from bs4 import BeautifulSoup as bs
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from konlpy.tag import Okt
from collections import Counter
import re
import os
from dotenv import load_dotenv
load_dotenv()

st.write("# 아카라 카페! 👋")

class NaverCafeCrawler:
    def __init__(self, driver_path, url, id, pw, baseurl, clubid, userDisplay, boardType):
        self.total_list = ['제목', '내용', '링크']
        self.driver_path = driver_path
        self.url = url
        self.id = id
        self.pw = pw
        self.baseurl = baseurl
        self.baseraw = os.getenv('BASERAW')
        self.clubid = clubid
        self.userDisplay = userDisplay
        self.boardType = boardType

    def initialize_file(self, file_path='content.csv'):
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            wr = csv.writer(f)
            wr.writerow([self.total_list[0], self.total_list[1], self.total_list[2]])

    def login(self, browser):
        browser.get(self.url)
        browser.implicitly_wait(2)
        browser.execute_script(f"document.getElementsByName('id')[0].value='{self.id}'")
        browser.execute_script(f"document.getElementsByName('pw')[0].value='{self.pw}'")
        browser.find_element(By.XPATH, '//*[@id="log.login"]').click()
        time.sleep(1)

    def crawl_page(self, browser, page_num):
        browser.get(f"{self.baseurl}ArticleList.nhn?search.clubid={self.clubid}&userDisplay={self.userDisplay}"
                    f"&search.boardType={self.boardType}&search.page={page_num}")
        browser.switch_to.frame('cafe_main')
        soup = bs(browser.page_source, 'html.parser')
        soup = soup.find_all(class_='article-board m-tcol-c')[1]
        datas = soup.find_all(class_='td_article')
        new_df = pd.DataFrame(columns=['제목', '내용', '링크'])
        
        #print(datas)
        for data in datas:
            article_title = data.find(class_='article')
            link = article_title.get('href')
            article_title = article_title.get_text().strip()
            content = self.get_content(browser, self.baseraw + link)
            new_df = pd.concat([new_df, pd.DataFrame({'제목': [article_title], '내용': [content], '링크': [self.baseraw + link]})],
                              ignore_index=True)
        return new_df

    def get_content(self, browser, link):
        browser.get(link)
        time.sleep(1)
        browser.switch_to.frame('cafe_main')
        soup = bs(browser.page_source, 'html.parser')
        content = soup.find("div",{"class":"article_viewer"})
        
        if content:
            #print(f"Content: {content.get_text().strip()}")
            #print("\n")
            return content.get_text().strip()
        else:
            return ""

    def run(self, max_pages=2, file_path='content.csv'):
        self.initialize_file(file_path)
        offset = 0
        i = offset
        while i < max_pages+offset:
            i += 1
            pageNum = i
            print(f"Page Number: {pageNum}")
            original_df = pd.read_csv(file_path, encoding='utf-8')
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument(f'--webdriver-path={self.driver_path}')
            browser = webdriver.Chrome(options=chrome_options)
            self.login(browser)
            new_df = self.crawl_page(browser, pageNum)
            concat_df = pd.concat([original_df, new_df])
            concat_df = concat_df.drop_duplicates(keep=False)
            concat_df.to_csv(file_path, mode='a', header=False, index=False)
            browser.close()
            time.sleep(5)
        print("done completely....")

if __name__ == "__main__":
    driver_path = os.getenv('DRIVER_PATH')  # Update this path to your chromedriver location
    url = os.getenv('URL')
    id = os.getenv('ID')
    pw = os.getenv('PWD')
    baseurl = os.getenv('BASEURL')
    clubid = os.getenv('CLUBID')  # aqara
    userDisplay = 10
    boardType = 'L'
    params_pages = st.slider("게시판 페이지 수",min_value=1,max_value=100,step=1,value=1)
    params_display = st.slider("보여줄 데이터 수", min_value=1,max_value=10,step=1,value=5)
    

    crawler = NaverCafeCrawler(driver_path, url, id, pw, baseurl, clubid, userDisplay, boardType)
    crawler.run(max_pages=params_pages)
    df = pd.read_csv("content.csv")
    st.table(df.loc[:,["제목","내용"]].dropna().head(params_display))

    # Define the list of Korean device names to analyze
korean_device_names_to_analyze = ['스마트 싱스','홈킷','애플 홈킷','매터','matter','Matter','허브', '센서', '플러그', '콘센트', '조명스위치', '블라인드', '커튼', '카메라', '도어락','온습도','조도','누수','스위치','무선 스위치']

# Extract Korean device names from the text using regular expressions
korean_device_names = []
print(df['내용'])
if len(df.dropna())!=0:

    for text in df.dropna()['내용']:
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


