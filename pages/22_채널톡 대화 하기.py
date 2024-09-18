import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

import os
from dotenv import load_dotenv
load_dotenv()

# Account Information

channeltalk_access_key = os.getenv('CHANNELTALK_ACCESS_KEY')
channeltalk_access_secret = os.getenv('CHANNELTALK_ACCESS_SECRET')


# Set page configuration
st.set_page_config(page_title="채널톡 대화", page_icon="💬", layout="wide")

# Page header
st.write("# 채널톡! 👋")


# Calculate yesterday and today for the query
yesterday = datetime.now() - timedelta(days=1)
today = datetime.now()

# API endpoint and authentication information
url = "https://api.channel.io/open/v5/user-chats"
headers = {
    "accept": "application/json",
    "x-access-key": f"{channeltalk_access_key}",
    "x-access-secret": f"{channeltalk_access_secret}"
}

# Parameters for the API request
params_sort = "desc"
params_limit = st.slider("검색 데이터 수", min_value=20, max_value=500, step=20, value=100)
params_display = st.slider("보여줄 데이터 수", min_value=1, max_value=10, step=1, value=5)
params_state_temp = st.selectbox("고객 지원 완료 여부", ("새질문 또는 답변 중", "답변 완료"))
params_state = "closed" if params_state_temp == "답변 완료" else "opened"

params = {
    "state": params_state,
    "sortOrder": params_sort,
    "limit": params_limit,
    "from": int(yesterday.timestamp() * 1000),  # Start of yesterday
    "to": int(today.timestamp() * 1000)  # Up to now
}

# Function to get messages
def get_messages():
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        chats = data.get("messages", [])
        user_chats = data.get("userChats", [])
        return pd.DataFrame(chats), pd.DataFrame(user_chats)
    else:
        st.error(f"API 요청에 실패하였습니다. 상태 코드: {response.status_code}, 응답: {response.text}")
        return pd.DataFrame(), pd.DataFrame()

# Get messages
df_chats, df_user_chats = get_messages()

if not df_chats.empty:
    # Create 'text' column based on 'plainText'
    df_chats['text'] = df_chats['plainText']

    # Convert 'updatedAt' to datetime format
    df_chats['updatedAt'] = pd.to_datetime(df_chats['updatedAt'], unit='ms') + pd.Timedelta(hours=9)

    # Determine the sender
    df_chats['sender'] = df_chats['personType'].apply(lambda x: "Manager" if x == "manager" else "Customer")

    # Sort by 'updatedAt' to get the latest messages
    df_sorted = df_chats[['id', 'updatedAt', 'text', 'sender', 'chatId']].dropna().sort_values(by='updatedAt', ascending=False).head(10)

    # Display the sorted DataFrame
    st.write("### 최근 10개의 대화")
    st.table(df_sorted[['updatedAt', 'sender', 'text']])

    # Select a message to reply to
    selected_message = st.selectbox("답변할 메시지를 선택하세요:", df_sorted['text'].tolist())

    # Input field for reply with a unique key
    answer = st.text_area("답변 입력", value="", placeholder="여기에 답변을 입력하세요...", key="unique_answer_input")

    # Handle the reply button click
    if st.button("답변 전송"):
        try:
            # Retrieve the userChatId (chatId) corresponding to the selected message
            user_chat_id = df_sorted[df_sorted['text'] == selected_message]['chatId'].values[0]

            # Prepare the reply URL using the retrieved userChatId with the botName set to "스마트홈의 시작, 아카라 BOT"
            reply_url = f"https://api.channel.io/open/v5/user-chats/{user_chat_id}/messages?botName=스마트홈의 시작, 아카라 BOT"

            # Payload for the POST request
            payload = {
                "blocks": [
                    {
                        "type": "text",
                        "value": answer
                    }
                ],
                "options": ["actAsManager"]  # Ensuring the correct sender identity
            }

            # Sending a POST request to reply to the selected message
            reply_response = requests.post(reply_url, headers=headers, json=payload)

            if reply_response.status_code == 200:
                st.success("답변이 성공적으로 전송되었습니다.")
                # Clear the input field by resetting the text area with a new key
                st.text_area("답변 입력", value="", placeholder="여기에 답변을 입력하세요...", key="new_answer_input")
                st.experimental_rerun()  # Refresh the app to clear input and reload data
            else:
                st.error(f"답변 전송에 실패했습니다. 상태 코드: {reply_response.status_code}, 응답: {reply_response.text}")
        except IndexError:
            st.warning("선택한 메시지에 해당하는 ID를 찾을 수 없습니다.")

    # Add a button to refresh the page
    if st.button("페이지 새로고침"):
        st.experimental_rerun()  # Refresh the app to clear input and reload data
else:
    st.warning("검색 결과가 없습니다. 다른 필터를 시도해 보세요.")