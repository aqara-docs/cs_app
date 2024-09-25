import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import CountVectorizer
import seaborn as sns
import os
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch.nn.functional import softmax
import torch

load_dotenv()

plt.rcParams['font.family'] = 'AppleGothic'  # Mac의 경우 AppleGothic, Windows의 경우 Malgun Gothic 등을 사용합니다.

# MariaDB connection details
db_user = os.getenv('SQL_USER')
db_password = os.getenv('SQL_PASSWORD')
db_host = os.getenv('SQL_HOST')
db_database = os.getenv('SQL_DATABASE')

# Create SQLAlchemy engine with explicit charset and collation settings
engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_database}?charset=utf8mb4&collation=utf8mb4_general_ci")

# Streamlit app title
st.title("공식몰 상품평 분석")

# Function to fetch all data from aqara_cafe table
def fetch_aqara_cafe24_review_data():
    with engine.connect() as conn:
        query = "SELECT * FROM cafe24_review"
        df = pd.read_sql(query, con=conn)
    return df

# Load KcBERT model and tokenizer
@st.cache_resource
def load_kcbert_model():
    model = AutoModelForSequenceClassification.from_pretrained("beomi/kcbert-base", num_labels=3)
    tokenizer = AutoTokenizer.from_pretrained("beomi/kcbert-base")
    return model, tokenizer

# Perform sentiment analysis using KcBERT
def perform_kcbert_sentiment_analysis(text, model, tokenizer):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    outputs = model(**inputs)
    probs = softmax(outputs.logits, dim=-1)
    sentiment = torch.argmax(probs, dim=-1).item()

    # Map sentiment index to positive, neutral, negative
    if sentiment == 0:
        return {"positive": probs[0][0].item(), "neutral": 0, "negative": probs[0][2].item()}
    elif sentiment == 1:
        return {"positive": 0, "neutral": probs[0][1].item(), "negative": 0}
    else:
        return {"positive": 0, "neutral": 0, "negative": probs[0][2].item()}

# Visualize sentiment analysis results over time
def visualize_sentiments_over_time(df):
    st.subheader("시간에 따른 감성 분석 시각화")

    # Group by date and calculate mean sentiment scores
    df_grouped = df.groupby('registered_date')[['positive', 'neutral', 'negative']].mean()

    # Plot the sentiment scores over time
    plt.figure(figsize=(10, 6))
    plt.plot(df_grouped.index, df_grouped['positive'], label='Positive', color='green')
    plt.plot(df_grouped.index, df_grouped['neutral'], label='Neutral', color='gray')
    plt.plot(df_grouped.index, df_grouped['negative'], label='Negative', color='red')
    plt.xlabel('Date')
    plt.ylabel('Sentiment Score')
    plt.title('Sentiment Analysis Over Time')
    plt.legend()
    plt.xticks(rotation=45)
    
    st.pyplot(plt)

# Perform word frequency analysis
def perform_word_frequency_analysis(df, n_words=50):
    st.subheader(f"상위 {n_words}개의 빈도 높은 단어 시각화")
    
    # Combine 'contents' column for word frequency analysis
    text_data = df['contents'].astype(str) 

    # Use CountVectorizer to get word frequencies
    vectorizer = CountVectorizer(max_features=n_words, stop_words='english')
    word_matrix = vectorizer.fit_transform(text_data)
    word_freq = pd.DataFrame(word_matrix.toarray(), columns=vectorizer.get_feature_names_out())
    
    # Sum up word frequencies over all rows
    word_freq_sum = word_freq.sum().sort_values(ascending=False)
    
    # Visualize word frequencies
    plt.figure(figsize=(10, 6))
    sns.barplot(x=word_freq_sum.values, y=word_freq_sum.index, palette="viridis")
    plt.xlabel("Frequency")
    plt.ylabel("Word")
    plt.title(f"Top {n_words} Most Frequent Words")
    st.pyplot(plt)

    # Analyze word frequencies over time
    df_words_over_time = pd.concat([df[['registered_date']], word_freq], axis=1)
    df_grouped = df_words_over_time.groupby('registered_date').sum()

    # Plot word frequencies over time
    plt.figure(figsize=(10, 6))
    for word in word_freq_sum.index:
        plt.plot(df_grouped.index, df_grouped[word], label=word)
    
    plt.xlabel('Date')
    plt.ylabel('Word Frequency')
    plt.title(f"Top {n_words} Word Frequency Over Time")
    plt.legend(loc='upper right', bbox_to_anchor=(1.25, 1))
    plt.xticks(rotation=45)
    st.pyplot(plt)

# Load data
df = fetch_aqara_cafe24_review_data()

# Convert registered_date to datetime format
df['registered_date'] = pd.to_datetime(df['registered_date'], errors='coerce')

# Load KcBERT model and tokenizer
kcbert_model, kcbert_tokenizer = load_kcbert_model()

# User selects the type of analysis
analysis_type = st.radio("분석 유형 선택", ("감성 분석", "단어 빈도 분석"))

if analysis_type == "감성 분석":
    st.subheader("데이터에 대한 감성 분석 수행")
    if 'contents' not in df.columns:
        st.error("감성 분석을 수행할 contents 칼럼이 없습니다.")
    else:
        # Combine 'contents' column for sentiment analysis
        df['combined_text'] = df['contents'].astype(str)

        # Apply sentiment analysis on the combined text
        df['sentiment'] = df['combined_text'].apply(lambda x: perform_kcbert_sentiment_analysis(x, kcbert_model, kcbert_tokenizer))
        df['positive'] = df['sentiment'].apply(lambda x: x['positive'])
        df['neutral'] = df['sentiment'].apply(lambda x: x['neutral'])
        df['negative'] = df['sentiment'].apply(lambda x: x['negative'])

        # Show the sentiment analysis results
        st.write("감성 분석 결과:")
        st.dataframe(df[['combined_text', 'registered_date', 'positive', 'neutral', 'negative']])

        # Visualize the sentiment analysis results over time
        visualize_sentiments_over_time(df)

elif analysis_type == "단어 빈도 분석":
    st.subheader("단어 빈도 분석 수행")
    if 'contents' not in df.columns:
        st.error("단어 빈도 분석을 수행할 contents 칼럼이 없습니다.")
    else:
        # Perform word frequency analysis
        perform_word_frequency_analysis(df)