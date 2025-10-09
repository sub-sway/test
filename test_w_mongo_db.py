import streamlit as st
import ssl
import threading
import time
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime, timedelta, UTC
import queue

# ==========================
# [보안 수정] Streamlit Secrets에서 연결 정보 가져오기
# ==========================
BROKER = st.secrets["mqtt"]["BROKER"]
PORT = st.secrets["mqtt"]["PORT"]
USERNAME = st.secrets["mqtt"]["USERNAME"]
PASSWORD = st.secrets["mqtt"]["PASSWORD"]
TOPIC = "multiSensor/numeric"

MONGO_URI = st.secrets["mongodb"]["MONGO_URI"]

# ==========================
# MongoDB 연결 설정
# ==========================
client = MongoClient(MONGO_URI)
db = client["SensorDB"]
collection = db["SensorData"]

# ==========================
# st.session_state 및 큐 초기화
# ==========================
if 'latest_message' not in st.session_state:
    st.session_state.latest_message = "아직 데이터 없음"
if 'message_count' not in st.session_state:
    st.session_state.message_count = 0
if 'data_queue' not in st.session_state:
    st.session_state.data_queue = queue.Queue()

# ==========================
# MQTT 콜백 함수
# ==========================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT 브로커 연결 성공")
        client.subscribe(TOPIC)
    else:
        print(f"❌ MQTT 연결 실패: code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode().strip()
        userdata.put(payload)
        print(f"📩 [수신됨, 큐에 추가] {payload}")
    except Exception as e:
        print(f"⚠️ 메시지 수신 중 오류: {e}")

# ==========================
# MQTT 스레드 함수
# ==========================
def mqtt_thread(q):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.user_data_set(q)
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
# Streamlit UI
# ==========================
st.set_page_config(page_title="PORTY Sensor Dashboard", layout="wide")
st.title("☁️ PORTY Sensor Dashboard")
st.write("---")

# MQTT 스레드는 최초 한 번만 실행되도록 설정
if "mqtt_started" not in st.session_state:
    threading.Thread(target=mqtt_thread, args=(st.session_state.data_queue,), daemon=True).start()
    st.session_state.mqtt_started = True

# --- UI 그리기 및 데이터 처리 ---

# 큐에 있는 모든 데이터를 메인 스레드에서 처리
while not st.session_state.data_queue.empty():
    payload = st.session_state.data_queue.get()
    st.session_state.latest_message = payload
    st.session_state.message_count += 1
    
    parts = payload.split(",")
    if len(parts) == 9:
        try:
            data_dict = {
                "timestamp": datetime.now(UTC),
                "CH4": float(parts[0]), "EtOH": float(parts[1]), "H2": float(parts[2]),
                "NH3": float(parts[3]), "CO": float(parts[4]), "NO2": float(parts[5]),
                "Oxygen": float(parts[6]), "Distance": float(parts[7]), "Flame": int(parts[8])
            }
            collection.insert_one(data_dict)
        except (ValueError, IndexError) as e:
            print(f"⚠️ 데이터 파싱 또는 DB 저장 오류: {e}, payload: {payload}")
    else:
        print(f"⚠️ 데이터 형식 오류: {payload}")

# 상단 상태 정보 표시
st.subheader("📡 실시간 수신 상태")
records = list(collection.find().sort("timestamp", -1).limit(1000))
status_cols = st.columns(3)

with status_cols[0]:
    st.metric("현재 시간", datetime.now().strftime("%H:%M:%S"))

# [오류 수정] records가 있을 때와 없을 때를 명확히 구분하여 처리
if records:
    last_reception_utc = records[0]['timestamp']
    last_reception_kst = last_reception_utc + timedelta(hours=9)
    time_diff = datetime.now(UTC) - last_reception_utc

    with status_cols[1]:
        st.metric("마지막 수신 시간 (KST)", last_reception_kst.strftime("%H:%M:%S"))
    
    with status_cols[2]:
        if time_diff.total_seconds() < 10:
            st.success("🟢 실시간 수신 중")
        else:
            st.warning(f"🟠 {int(time_diff.total_seconds())}초 동안 수신 없음")
else:
    with status_cols[1]:
        st.metric("마지막 수신 시간", "N/A")
    with status_cols[2]:
        st.info("수신 대기 중...")

flame_alert = st.empty()

if records:
    df = pd.DataFrame(reversed(records))
    latest_flame = int(df["Flame"].iloc[-1])
    if latest_flame == 0:
        flame_alert.error("🔥 불꽃 감지됨! 즉시 확인이 필요합니다!", icon="🔥")
    else:
        flame_alert.success("🟢 정상 상태 (불꽃 없음)", icon="✅")

    st.subheader("📊 현재 센서 값")
    sensors = ["CH4", "EtOH", "H2", "NH3", "CO", "NO2", "Oxygen", "Distance", "Flame"]
    metric_cols = st.columns(5)
    
    latest_data = df.iloc[-1]
    
    col_index = 0
    for sensor in sensors:
        with metric_cols[col_index % 5]:
             if sensor in latest_data:
                if sensor == "Flame":
                    state = "🔥 감지됨" if latest_data[sensor] == 0 else "🟢 정상"
                    st.metric(label="불꽃 상태", value=state)
                else:
                    st.metric(label=f"{sensor} 현재값", value=f"{latest_data[sensor]:.3f}")
        col_index +=1

    st.write("---")

    st.subheader("📈 센서별 실시간 변화 추세 (최신 1000개)")
    sensors_for_graph = ["CH4", "EtOH", "H2", "NH3", "CO", "NO2", "Oxygen", "Distance"]
    
    for i in range(0, len(sensors_for_graph), 3):
        graph_cols = st.columns(3)
        for j, sensor in enumerate(sensors_for_graph[i:i+3]):
            if i + j < len(sensors_for_graph):
                with graph_cols[j]:
                    if sensor in df.columns:
                        fig = px.line(df, x="timestamp", y=sensor, title=f"{sensor} 변화 추세", labels={"timestamp": "시간", sensor: "값"})
                        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"'{sensor}' 데이터를 찾을 수 없습니다.")
else:
    st.info("아직 MongoDB에 저장된 데이터가 없습니다. 센서 데이터를 기다리는 중...")

# 2초마다 스크립트 전체를 다시 실행하여 화면을 갱신
time.sleep(2)
st.rerun()

