import streamlit as st
import ssl, threading, time
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.express as px

# ==========================
# HiveMQ Cloud 연결 정보
# ==========================
BROKER = "8e008ba716c74e97a3c1588818ddb209.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "Arduino"
PASSWORD = "One24511"
TOPIC = "multiSensor/numeric"

# ==========================
# 전역 변수 (스레드 공유)
# ==========================
latest_message_global = "아직 데이터 없음"
message_count_global = 0
data_buffer = []   # 수신 데이터 저장용 (최근 100개)
connected = False

# ==========================
# MQTT 콜백 함수
# ==========================
def on_connect(client, userdata, flags, rc, properties=None):
    global connected
    if rc == 0:
        connected = True
        print("✅ MQTT 브로커 연결 성공")
        client.subscribe(TOPIC)
    else:
        print("❌ MQTT 연결 실패:", rc)

def on_message(client, userdata, msg):
    global latest_message_global, message_count_global, data_buffer
    try:
        payload = msg.payload.decode().strip()
        latest_message_global = payload
        message_count_global += 1
        print(f"📩 [수신됨] {payload}")

        parts = payload.split(",")
        if len(parts) == 9:
            data_dict = {
                "CH4": float(parts[0]),
                "EtOH": float(parts[1]),
                "H2": float(parts[2]),
                "NH3": float(parts[3]),
                "CO": float(parts[4]),
                "NO2": float(parts[5]),
                "Oxygen": float(parts[6]),
                "Distance": float(parts[7]),
                "Flame": int(parts[8])
            }
            data_buffer.append(data_dict)
            # 최근 100개까지만 유지
            if len(data_buffer) > 100:
                data_buffer = data_buffer[-100:]
        else:
            print("⚠️ 데이터 파싱 오류:", payload)
    except Exception as e:
        print("⚠️ 수신 처리 중 오류:", e)

# ==========================
# MQTT 스레드 함수
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
        print("❌ HiveMQ 연결 실패:", e)

# ==========================
# Streamlit UI
# ==========================
st.set_page_config(page_title="HiveMQ 실시간 센서 시각화", layout="centered")
st.title("☁️ HiveMQ Cloud MQTT 실시간 센서 시각화")
st.write("---")

if "mqtt_started" not in st.session_state:
    threading.Thread(target=mqtt_thread, daemon=True).start()
    st.session_state.mqtt_started = True

status_box = st.empty()
message_box = st.empty()
chart_box = st.empty()

# ==========================
# 주기적 갱신 루프
# ==========================
while True:
    status_box.markdown(f"**📊 수신된 메시지 수:** {message_count_global}")
    message_box.code(latest_message_global, language="text")

    if len(data_buffer) > 0:
        df = pd.DataFrame(data_buffer)
        fig = px.line(
            df.tail(50), 
            y=["CH4", "EtOH", "H2", "NH3", "CO", "NO2", "Oxygen"],
            title="📈 최근 센서 데이터 (최근 50개 샘플)",
            labels={"value": "측정값", "index": "시간 순서"}
        )
        chart_box.plotly_chart(fig, use_container_width=True)
    else:
        chart_box.info("아직 수신된 데이터가 없습니다...")

    time.sleep(2)
