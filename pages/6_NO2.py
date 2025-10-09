import streamlit as st
import pandas as pd
import plotly.express as px
import time

st.set_page_config(layout="wide")

# 페이지 제목 설정
st.title("📈 NO2 센서 그래프")

# st.session_state에 데이터가 있는지 확인
if 'df' not in st.session_state or st.session_state.df.empty:
    st.warning("메인 페이지에서 데이터가 수신될 때까지 기다려주세요...")
    st.stop()  # 데이터가 없으면 실행 중지

# 그래프를 표시할 플레이스홀더
chart_placeholder = st.empty()

# 그래프를 한 번만 생성하고, 새로운 데이터가 들어올 때마다 그래프를 갱신
while True:
    df_to_display = st.session_state.df.tail(1000)

    # 새로운 데이터로 '현재 값' 갱신
    st.subheader("현재 값")
    st.metric(label="NO2 현재값", value=f"{df_to_display['NO2'].iloc[-1]:.3f}")

    # 그래프 그리기
    fig = px.line(df_to_display, y="NO2", title="NO2 센서 실시간 데이터")
    
    # 고유한 key를 생성하여 plotly 차트에 할당, 그래프를 업데이트
    unique_key = f"chart_no2_{int(time.time())}"
    chart_placeholder.plotly_chart(fig, use_container_width=True, key=unique_key)

    time.sleep(2)  # 2초마다 그래프 갱신
