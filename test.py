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
data_buffer = []   # 최근 100개 데이터 버퍼
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
            # 🔄 Flame: 0 = 감지됨, 1 = 정상
            data_dict = {
                "CH4": float(parts[0]),
                "EtOH": float(parts[1]),
                "H2": float(parts[2]),
                "NH3": float(parts[3]),
                "CO": float(parts[4]),
                "NO2": float(parts[5]),
                "Oxygen": float(parts[6]),
                "Distance": float(parts[7]),
                "Flame": int(parts[8])  # 그대로 받아서 나중에 반전 처리
            }
            data_buffer.append(data_dict)
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
st.set_page_config(page_title="HiveMQ 실시간 센서 시각화", layout="wide")
st.title("☁️ HiveMQ Cloud MQTT 실시간 센서 시각화 (🔥 불꽃 감지 포함)")
st.write("---")

if "mqtt_started" not in st.session_state:
    threading.Thread(target=mqtt_thread, daemon=True).start()
    st.session_state.mqtt_started = True

# 화면 영역 확보
status_box = st.empty()
message_box = st.empty()
chart_placeholder = st.empty()
flame_alert = st.empty()

# ==========================
# 주기적 갱신 루프
# ==========================
while True:
    status_box.markdown(f"**📊 수신된 메시지 수:** {message_count_global}")
    message_box.code(latest_message_global, language="text")

    if len(data_buffer) > 0:
        df = pd.DataFrame(data_buffer)
        latest_flame = int(df["Flame"].iloc[-1])

        # Flame 상태 표시 (0 감지됨, 1 정상)
        if latest_flame == 0:
            flame_alert.error("🔥 불꽃 감지됨! 위험 감지 중!")
        else:
            flame_alert.success("🟢 정상 상태 (불꽃 없음)")

        # 여러 센서를 개별 그래프로 표시 (3열 x 3행)
        sensors = ["CH4","EtOH","H2","NH3","CO","NO2","Oxygen","Distance","Flame"]
        chart_placeholder.empty()  # 갱신 전 초기화
        with chart_placeholder.container():
            st.subheader("📈 센서별 꺾은선 그래프 (최근 100개 샘플)")
            for i in range(0, len(sensors), 3):
                cols = st.columns(3)
                for j, sensor in enumerate(sensors[i:i+3]):
                    with cols[j]:
                        if sensor in df:
                            fig = px.line(
                                df.tail(100),
                                y=sensor,
                                title=f"{sensor} 변화 추세",
                                labels={"index": "시간 순서", sensor: "값"}
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            if sensor == "Flame":
                                state = "🔥 감지됨" if latest_flame == 0 else "🟢 정상"
                                st.metric(label="Flame 상태", value=state)
                            else:
                                st.metric(label=f"{sensor} 현재값", value=f"{df[sensor].iloc[-1]:.3f}")
    else:
        chart_placeholder.info("아직 수신된 데이터가 없습니다...")

    time.sleep(2)
