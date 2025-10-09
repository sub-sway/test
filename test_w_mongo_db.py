import streamlit as st
import ssl
import threading
import time
import paho.mqtt.client as mqtt
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from queue import Queue

# ==========================
# HiveMQ Cloud 및 MongoDB 연결 정보
# ==========================
BROKER = "8e008ba716c74e97a3c1588818ddb209.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "Arduino"
PASSWORD = "One24511"
TOPIC = "multiSensor/numeric"

MONGO_URI = "mongodb+srv://jystarwow_db_user:zf01VaAW4jYH0dVP@porty.oqiwzud.mongodb.net/"

# ==========================
# MQTT 콜백 함수
# ==========================
data_queue = Queue()
latest_message_global = "아직 데이터 없음"
message_count_global = 0

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT 브로커 연결 성공")
        client.subscribe(TOPIC)
    else:
        print(f"❌ MQTT 연결 실패: {rc}")

def on_message(client, userdata, msg):
    global latest_message_global, message_count_global
    try:
        payload = msg.payload.decode().strip()
        latest_message_global = payload
        message_count_global += 1
        
        parts = payload.split(",")
        if len(parts) == 9:
            data = {
                "timestamp": datetime.utcnow(),
                "CH4": float(parts[0]), "EtOH": float(parts[1]), "H2": float(parts[2]),
                "NH3": float(parts[3]), "CO": float(parts[4]), "NO2": float(parts[5]),
                "Oxygen": float(parts[6]), "Distance": float(parts[7]), "Flame": int(parts[8]),
            }
            # 큐에 데이터 추가
            data_queue.put(data)
        else:
            print(f"⚠️ 데이터 포맷 오류: {payload}")
    except Exception as e:
        print(f"⚠️ 메시지 처리 중 오류: {e}")

# ==========================
# MQTT 스레드
# ==========================
def mqtt_thread():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT)
        client.loop_forever()
    except Exception as e:
        print(f"❌ HiveMQ 연결 실패: {e}")

# ==========================
# Streamlit 앱 시작점
# ==========================

# --- 페이지 설정 ---
st.set_page_config(page_title="실시간 센서 대시보드", layout="wide")
st.title("☁️ 실시간 센서 데이터 개요")
st.info("왼쪽 사이드바에서 센서별 상세 그래프를 확인하세요.")

# --- st.session_state 초기화 (최초 1회만 실행) ---
if 'db_initialized' not in st.session_state:
    print("🚀 DB 및 세션 상태 초기화...")
    client = MongoClient(MONGO_URI)
    db = client["SensorDB"]
    st.session_state.collection = db["SensorData"]
    
    initial_records = list(st.session_state.collection.find().sort("timestamp", -1).limit(1000))
    if initial_records:
        st.session_state.df = pd.DataFrame(reversed(initial_records))
    else:
        st.session_state.df = pd.DataFrame(columns=["timestamp", "CH4", "EtOH", "H2", "NH3", "CO", "NO2", "Oxygen", "Distance", "Flame"])
    
    st.session_state.db_initialized = True

# --- MQTT 스레드 시작 (최초 1회만 실행) ---
if "mqtt_started" not in st.session_state:
    print("🚀 MQTT 스레드 시작...")
    threading.Thread(target=mqtt_thread, daemon=True).start()
    st.session_state.mqtt_started = True

# ==========================
# Streamlit 주기적 갱신 (메인 페이지)
# ==========================
status_box = st.empty()
message_box = st.empty()
flame_alert = st.empty()

while True:
    # 큐에서 데이터를 가져와 st.session_state.df 업데이트
    while not data_queue.empty():
        new_data = data_queue.get()
        new_df = pd.DataFrame([new_data])
        st.session_state.df = pd.concat([st.session_state.df, new_df], ignore_index=True)

    df_to_display = st.session_state.df.tail(1000)

    # --- 메인 페이지 UI 업데이트 ---
    status_box.markdown(f"**📊 수신 메시지:** {message_count_global} | **그래프 데이터:** {len(df_to_display)}")
    message_box.code(latest_message_global, language="text")

    if not df_to_display.empty:
        latest_flame = int(df_to_display["Flame"].iloc[-1])
        if latest_flame == 0:
            flame_alert.error("🔥 불꽃 감지됨! 위험!")
        else:
            flame_alert.success("🟢 정상 상태 (불꽃 없음)")

        st.subheader("📊 현재 센서 값")
        sensors = ["CH4", "EtOH", "H2", "NH3", "CO", "NO2", "Oxygen", "Distance"]
        cols = st.columns(4)  # 4개의 열로 센서 값 표시
        for i, sensor in enumerate(sensors):
            with cols[i % 4]:
                st.metric(label=f"{sensor} 현재값", value=f"{df_to_display[sensor].iloc[-1]:.3f}")
    else:
        st.info("수신 대기 중... 아직 데이터가 없습니다.")

    time.sleep(2)
