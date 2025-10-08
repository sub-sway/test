import streamlit as st
import ssl, threading
import paho.mqtt.client as mqtt
from streamlit_autorefresh import st_autorefresh

# -------------------------------
# HiveMQ Cloud 접속 정보
# -------------------------------
BROKER = "8e008ba716c74e97a3c1588818ddb209.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "Arduino"
PASSWORD = "One24511"
TOPIC = "multiSensor/numeric"

# -------------------------------
# 전역 버퍼 (Thread-safe 중계용)
# -------------------------------
latest_message_global = None
message_count_global = 0

# -------------------------------
# Streamlit 상태 초기화
# -------------------------------
st.set_page_config(page_title="HiveMQ MQTT 테스트", layout="centered")

if "latest_message" not in st.session_state:
    st.session_state.latest_message = "아직 데이터 없음"
if "message_count" not in st.session_state:
    st.session_state.message_count = 0
if "mqtt_started" not in st.session_state:
    st.session_state.mqtt_started = False

# -------------------------------
# MQTT 콜백
# -------------------------------
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT 브로커 연결 성공")
        client.subscribe(TOPIC)
    else:
        print("❌ 연결 실패, 코드:", rc)

def on_message(client, userdata, msg):
    global latest_message_global, message_count_global
    try:
        payload = msg.payload.decode().strip()
        latest_message_global = payload
        message_count_global += 1
        print(f"📩 [수신됨] {payload}")
    except Exception as e:
        print("⚠️ MQTT 수신 오류:", e)

# -------------------------------
# MQTT 스레드 함수
# -------------------------------
def mqtt_thread():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set(
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS,
        ciphers=None
    )
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT)
        client.loop_forever()
    except Exception as e:
        print("❌ HiveMQ 연결 실패:", e)

# -------------------------------
# MQTT 스레드 시작 (1회만)
# -------------------------------
if not st.session_state.mqtt_started:
    threading.Thread(target=mqtt_thread, daemon=True).start()
    st.session_state.mqtt_started = True

# -------------------------------
# Streamlit UI (2초마다 갱신)
# -------------------------------
st_autorefresh(interval=2000, key="refresh")

# MQTT 스레드 → 세션 상태로 동기화
if latest_message_global:
    st.session_state.latest_message = latest_message_global
    st.session_state.message_count = message_count_global

# -------------------------------
# 화면 표시
# -------------------------------
st.title("☁️ HiveMQ Cloud MQTT 수신 테스트")
st.write("---")

st.write(f"📡 **Broker**: `{BROKER}`")
st.write(f"🧩 **Topic**: `{TOPIC}`")
st.write(f"📊 **수신된 메시지 수**: {st.session_state.message_count}")

st.subheader("📥 최근 수신 메시지")
st.code(st.session_state.latest_message, language="text")

st.info("ESP32/Arduino → HiveMQ Cloud → Streamlit 데이터 테스트 중입니다.")
