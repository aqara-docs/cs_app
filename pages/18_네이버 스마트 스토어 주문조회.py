import streamlit as st
import http.client
import json
import requests
import time
import bcrypt
import pybase64
import urllib.parse

import os
from dotenv import load_dotenv
load_dotenv()
# Set up Streamlit page
st.write("# 네이버 스마트 스토어 주문번호 조회!")

# Account Information

smartstore_client_id = os.getenv('SMARTSTORE_CLIENT_ID')
smartstore_client_secret = os.getenv('SMARTSTORE_CLIENT_SECRET')

# Get Token function
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

        body = urllib.parse.urlencode(data_)

        url = 'https://api.commerce.naver.com/external/v1/oauth2/token'
        res = requests.post(url=url, headers=headers, data=body)
        res.raise_for_status()

        res_data = res.json()
        if 'access_token' in res_data:
            return res_data['access_token']
        else:
            raise ValueError(f'Token request failed: {res_data}')
    
    except Exception as e:
        print(f'Error occurred: {e}')
        return None

# Fetch the product order IDs using the main order number
def fetch_product_order_ids(order_no, token):
    try:
        conn = http.client.HTTPSConnection("api.commerce.naver.com")
        headers = { 'Authorization': f"Bearer {token}" }

        # Request for product order IDs based on the order number
        conn.request("GET", f"/external/v1/pay-order/seller/orders/{order_no}/product-order-ids", headers=headers)

        res = conn.getresponse()
        data = res.read()
        conn.close()

        # Convert the response to JSON format
        return json.loads(data.decode("utf-8"))

    except Exception as e:
        st.error(f"Error fetching product order IDs: {e}")
        return None

# Fetch detailed order information using product order IDs
def fetch_order_details(product_order_ids, token):
    try:
        conn = http.client.HTTPSConnection("api.commerce.naver.com")

        # JSON payload containing the product order IDs
        payload = json.dumps({
            "productOrderIds": product_order_ids
        })

        headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/json"
        }

        # Make the POST request to fetch the order details
        conn.request("POST", "/external/v1/pay-order/seller/product-orders/query", payload, headers)

        res = conn.getresponse()
        data = res.read()
        conn.close()

        # Convert the response to JSON format and return it
        return json.loads(data.decode("utf-8"))
    
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Get the access token
st_access_token = get_token(client_id=smartstore_client_id, client_secret=smartstore_client_secret)

# Step 1: User inputs the main order number to fetch product order IDs
order_no = st.text_input("주문번호 입력")

if st.button("주문 상세 조회"):
    if order_no:
        product_order_ids_data = fetch_product_order_ids(order_no, st_access_token)
        
        if product_order_ids_data and "data" in product_order_ids_data:
            product_order_ids = product_order_ids_data["data"]
            
            if product_order_ids:
                # Fetch and display the details for all product order IDs
                order_details = fetch_order_details(product_order_ids, st_access_token)
                
                if order_details:
                    st.write("### 주문 상세 정보")
                    st.json(order_details)
            else:
                st.warning("해당 주문번호에 대한 상품 주문번호가 없습니다.")
    else:
        st.warning("주문번호를 입력하세요.")