import streamlit as st
import pandas as pd
import mysql.connector
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(page_title="Server Ledger Search", page_icon="🔍", layout="wide")

# MySQL Database configuration
db_config = {
    'user': os.getenv('SQL_USER'),
    'password': os.getenv('SQL_PASSWORD'),
    'host': os.getenv('SQL_HOST'),
    'database': os.getenv('SQL_DATABASE'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_general_ci'
}

# Function to fetch unique values from the database
def fetch_unique_values(column, table_name):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = f"SELECT DISTINCT {column} FROM {table_name}"
        cursor.execute(query)
        values = cursor.fetchall()
        values = [value[0] for value in values if value[0] is not None]  # Remove None values
        return values
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()

# Function to standardize "불량" and "고장" to "불량"
def standardize_reason(reason):
    if "불량" in reason or "고장" in reason:
        return "불량"
    return reason

# Function to search data based on filters
def search_data(registered_start, registered_end, reason, order_place, product):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT *
        FROM service_ledger
        WHERE registered_date BETWEEN %s AND %s
        """
        params = [registered_start, registered_end]

        if reason and reason != '전체':
            query += " AND 사유 = %s"
            params.append(reason)

        if order_place and order_place != '전체':
            query += " AND 주문처 = %s"
            params.append(order_place)

        if product and product != '전체':
            query += " AND 제품 = %s"
            params.append(product)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        # Convert datetime objects to string format for JSON serialization
        for row in rows:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.strftime('%Y-%m-%d %H:%M:%S')

        return pd.DataFrame(rows), rows
    except mysql.connector.Error as err:
        st.error(f"Error querying database: {err}")
        return pd.DataFrame(), []
    finally:
        cursor.close()
        conn.close()

# Fetch unique values for 사유, 주문처, and 제품
reasons = fetch_unique_values('사유', 'service_ledger')
order_places = fetch_unique_values('주문처', 'service_ledger')
products = fetch_unique_values('제품', 'service_ledger')

# "불량" 또는 "고장"을 포함하는 사유를 "불량"으로 통합
reasons = [standardize_reason(reason) for reason in reasons]
reasons = list(set(reasons))  # Remove duplicates after standardization

# Sort the reasons in descending order of frequency
reasons_freq = pd.Series(reasons).value_counts(ascending=False).index.tolist()
reasons_freq.insert(0, '전체')

# 주문처 리스트에 "전체" 추가
order_places.insert(0, '전체')

# 제품 리스트에 "전체" 추가
products.insert(0, '전체')

# 메인 페이지에 검색 필터 표시
st.header("Search Filters")

# Select 사유
selected_reason = st.selectbox("수거 사유", reasons_freq)

# Select 주문처
selected_order_place = st.selectbox("주문처", order_places)

# Select 제품
selected_product = st.selectbox("제품", products)

# Date range selection
default_start_date = datetime.now().replace(day=1)
selected_start_date = st.date_input("Start Date", value=default_start_date)
selected_end_date = st.date_input("End Date", value=datetime.now())

# Search button
if st.button("Search"):
    # Convert dates to string for SQL query
    registered_start_str = selected_start_date.strftime('%Y-%m-%d')
    registered_end_str = selected_end_date.strftime('%Y-%m-%d')

    # Fetch data based on filters
    df, json_data = search_data(registered_start_str, registered_end_str, selected_reason, selected_order_place, selected_product)

    if not df.empty:
        # Display DataFrame with selected columns
        st.subheader("Search Results (DataFrame)")
        st.dataframe(df[['registered_date', '사유', '주문번호', '고객명', '연락처', '제품', '수량', '비고']])

        # Display raw JSON data
        st.subheader("Search Results (JSON)")
        st.json(json.dumps(json_data, ensure_ascii=False, indent=4))
    else:
        st.warning("No data found for the given criteria.")