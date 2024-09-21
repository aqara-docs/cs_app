import streamlit as st
import subprocess

st.title("Streamlit에서 터미널 명령어 실행")

# 사용자로부터 터미널 명령어 입력 받기
command = st.text_input("실행할 터미널 명령어를 입력하세요:", value="ls")

# 명령어 실행 버튼
if st.button("명령어 실행"):
    try:
        # subprocess를 사용하여 명령어 실행
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 명령어 결과 출력
        st.subheader("출력 결과:")
        st.text(result.stdout)

        # 에러가 있는 경우 에러 출력
        if result.stderr:
            st.subheader("에러 메시지:")
            st.text(result.stderr)
    except Exception as e:
        st.write(f"명령어 실행 중 오류가 발생했습니다: {e}")