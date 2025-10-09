import streamlit as st
import ssl
import threading
import time
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import queue
import os
from streamlit_autorefresh import st_autorefresh # [추가] 자동 새로고침 라이브러리 임포트

# ==================================
# 설정 (Configurations) - 변경 없음
# ==================================
BROKER = "8e008ba716c74e97a3c1588818ddb209.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "Arduino"
PASSWORD = "One24511"
TOPIC = "multiSensor/numeric"
MONGO_URI = "mongodb+srv://jystarwow_db_user:zf01VaAW4jYH0dVP@porty.oqiwzud.mongodb.net/"
LOG_FILE = "sensor_logs.txt"
OXYGEN_SAFE_MIN = 19.5
OXYGEN_SAFE_MAX = 23.5
NO2_WARN_LIMIT = 3.0
NO2_DANGER_LIMIT = 5.0

# ==================================
# 헬퍼 함수 (Helper Functions)
# ==================================
@st.cache_resource
def get_mongo_collection():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster')
        print("✅ MongoDB 연결 성공")
        db = client["SensorDB"]
        return db["SensorData"]
    except Exception as e:
        st.error(f"MongoDB에 연결할 수 없습니다: {e}", icon="🚨")
        return None

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0: print("✅ MQTT 브로커 연결 성공"); client.subscribe(TOPIC)
    else: print(f"❌ MQTT 연결 실패: code {rc}")

def on_message(client, userdata, msg):
    try: userdata.put(msg.payload.decode().strip())
    except Exception as e: print(f"⚠️ 메시지 수신 중 오류: {e}")

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
    except Exception as e: print(f"❌ HiveMQ 연결 실패: {e}")

# ==================================
# Streamlit 앱 클래스
# ==================================
class SensorDashboard:
    def __init__(self):
        self.collection = get_mongo_collection()
        self._initialize_state()

    def _initialize_state(self):
        defaults = {
            'mqtt_started': False,
            'data_queue': queue.Queue(),
            'live_df': pd.DataFrame(),
            'last_sensor_values': {"CH4": 0.0, "EtOH": 0.0, "H2": 0.0, "NH3": 0.0, "CO": 0.0},
            'page': 'dashboard'
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def _start_mqtt_thread_once(self):
        if not st.session_state.mqtt_started:
            threading.Thread(target=mqtt_thread, args=(st.session_state.data_queue,), daemon=True).start()
            st.session_state.mqtt_started = True

    def _load_initial_data(self):
        if self.collection is not None and st.session_state.live_df.empty:
            try:
                records = list(self.collection.find().sort("timestamp", -1).limit(1000))
                if records:
                    st.session_state.live_df = pd.DataFrame(reversed(records))
                    print(f"✅ 초기 데이터 {len(st.session_state.live_df)}개 로드 완료")
            except Exception as e:
                print(f"⚠️ 초기 데이터 로딩 실패: {e}")

    def _process_mqtt_queue(self):
        new_data_list = []
        while not st.session_state.data_queue.empty():
            payload = st.session_state.data_queue.get()
            parts = payload.split(",")
            if len(parts) == 9:
                try:
                    data_dict = {"timestamp": datetime.now(timezone.utc), "CH4": float(parts[0]), "EtOH": float(parts[1]), "H2": float(parts[2]), "NH3": float(parts[3]), "CO": float(parts[4]), "NO2": float(parts[5]), "Oxygen": float(parts[6]), "Distance": float(parts[7]), "Flame": int(parts[8])}
                    new_data_list.append(data_dict)
                    self._check_and_log_alerts(data_dict)
                except (ValueError, IndexError) as e:
                    print(f"⚠️ 데이터 파싱 오류: {e}, payload: {payload}")
        if new_data_list:
            if self.collection is not None:
                self.collection.insert_many(new_data_list)
            new_df = pd.DataFrame(new_data_list)
            st.session_state.live_df = pd.concat([st.session_state.live_df, new_df], ignore_index=True).tail(1000)

    def _check_and_log_alerts(self, data_dict):
        # ... (이하 _check_and_log_alerts 메서드는 변경 없음) ...
        def log_alert(message):
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as log_file:
                    log_file.write(f"{datetime.now(timezone.utc).isoformat()} - {message}\n")
            except Exception as e: print(f"⚠️ 로그 파일 작성 오류: {e}")

        if data_dict.get("Flame") == 0: log_alert("🔥 불꽃 감지됨! 즉시 확인이 필요합니다!")
        oxygen_val = data_dict.get("Oxygen")
        if oxygen_val is not None and not (OXYGEN_SAFE_MIN <= oxygen_val <= OXYGEN_SAFE_MAX):
            log_alert(f"🟠 산소 농도 경고! 현재 값: {oxygen_val:.1f}%")
        no2_val = data_dict.get("NO2")
        if no2_val is not None:
            if no2_val >= NO2_DANGER_LIMIT: log_alert(f"🔴 이산화질소(NO2) 위험! 현재 값: {no2_val:.3f} ppm")
            elif no2_val >= NO2_WARN_LIMIT: log_alert(f"🟡 이산화질소(NO2) 주의! 현재 값: {no2_val:.3f} ppm")
        for sensor in ["CH4", "EtOH", "H2", "NH3", "CO"]:
            new_value = data_dict.get(sensor, 0.0)
            if new_value > 0 and st.session_state.last_sensor_values.get(sensor, 0.0) == 0:
                log_alert(f"🟡 {sensor} 가스 감지됨! 현재 값: {new_value:.3f}")
            st.session_state.last_sensor_values[sensor] = new_value

    def _handle_sidebar(self):
        st.sidebar.title("메뉴")
        if st.sidebar.button('📈 실시간 대시보드'):
            st.session_state.page = 'dashboard'
        if st.sidebar.button('📜 센서 이벤트 로그'):
            st.session_state.page = 'log'

    def _render_page(self):
        page_map = {
            'dashboard': self._draw_dashboard,
            'log': self._draw_log_page
        }
        page_function = page_map.get(st.session_state.page)
        if page_function:
            page_function()

    def _draw_dashboard(self):
        st.title("📈 실시간 대시보드")
        # ... (이하 대시보드 렌더링 로직은 기존과 동일) ...
        st.write("---")
        df = st.session_state.live_df
        st.subheader("📡 실시간 수신 상태")
        status_cols = st.columns(3)
        kst_offset = timedelta(hours=9)
        now_kst = datetime.now(timezone.utc) + kst_offset
        with status_cols[0]:
            st.metric("현재 시간 (KST)", now_kst.strftime("%H:%M:%S"))
        if not df.empty:
            last_reception_utc = df['timestamp'].iloc[-1].replace(tzinfo=timezone.utc)
            time_diff = datetime.now(timezone.utc) - last_reception_utc
            with status_cols[1]:
                st.metric("마지막 수신 시간 (KST)", (last_reception_utc + kst_offset).strftime("%H:%M:%S"))
            with status_cols[2]:
                if time_diff.total_seconds() < 10: st.success("🟢 실시간 수신 중")
                else: st.warning(f"🟠 {int(time_diff.total_seconds())}초 동안 수신 없음")
        else:
            with status_cols[1]: st.metric("마지막 수신 시간", "NA")
            with status_cols[2]: st.info("수신 대기 중...")
        st.subheader("🚨 종합 현재 상태")
        if not df.empty:
            latest_data = df.iloc[-1]
            flame_detected = latest_data["Flame"] == 0
            oxygen_unsafe = not (OXYGEN_SAFE_MIN <= latest_data["Oxygen"] <= OXYGEN_SAFE_MAX)
            no2_dangerous = latest_data["NO2"] >= NO2_DANGER_LIMIT
            no2_warning = latest_data["NO2"] >= NO2_WARN_LIMIT
            if flame_detected: st.error("🔥 불꽃 감지됨!", icon="🔥")
            if oxygen_unsafe: st.warning(f"🟠 산소 농도 경고! 현재 {latest_data['Oxygen']:.1f}%", icon="⚠️")
            if no2_dangerous: st.error(f"🔴 이산화질소(NO2) 농도 위험! 현재 {latest_data['NO2']:.3f} ppm", icon="☣️")
            elif no2_warning: st.warning(f"🟡 이산화질소(NO2) 농도 주의! 현재 {latest_data['NO2']:.3f} ppm", icon="⚠️")
            if not any([...]): st.success("✅ 안정 범위 내에 있습니다.", icon="👍")
        else:
            st.info("데이터 수신 대기 중...")
        if not df.empty:
            st.subheader("📊 현재 센서 값")
            sensors = ["CH4", "EtOH", "H2", "NH3", "CO", "NO2", "Oxygen", "Distance", "Flame"]
            metric_cols = st.columns(5)
            latest_data = df.iloc[-1]
            for i, sensor in enumerate(sensors):
                with metric_cols[i % 5]:
                    if sensor in latest_data:
                        if sensor == "Flame":
                            state = "🔥 감지됨" if latest_data[sensor] == 0 else "🟢 정상"
                            st.metric(label="불꽃 상태", value=state)
                        else:
                            st.metric(label=f"{sensor} 현재값", value=f"{latest_data[sensor]:.3f}")
            st.write("---")
            st.subheader("📈 센서별 실시간 변화 추세")
            sensors_for_graph = ["CH4", "EtOH", "H2", "NH3", "CO", "NO2", "Oxygen", "Distance"]
            for i in range(0, len(sensors_for_graph), 3):
                graph_cols = st.columns(3)
                for j, sensor in enumerate(sensors_for_graph[i:i+3]):
                    if i + j < len(sensors_for_graph):
                        with graph_cols[j]:
                            if sensor in df.columns:
                                fig = px.line(df, x="timestamp", y=sensor, title=f"{sensor} 변화 추세")
                                fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
                                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("아직 표시할 데이터가 없습니다.")

    def _draw_log_page(self):
        st.title("📜 센서 이벤트 로그")
        # ... (이하 로그 페이지 렌더링 로직은 기존과 동일) ...
        st.write("---")
        st.write("불꽃, 가스, 위험 농도 등이 감지될 때 기록된 로그를 최신순으로 보여줍니다.")
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    log_lines = f.readlines()
                if log_lines:
                    log_entries = []
                    for line in log_lines:
                        if " - " in line:
                            parts = line.split(" - ", 1)
                            utc_dt = datetime.fromisoformat(parts[0].replace('Z', '+00:00'))
                            kst_dt = utc_dt.astimezone(timezone(timedelta(hours=9)))
                            log_entries.append({"감지 시간 (KST)": kst_dt.strftime('%Y-%m-%d %H:%M:%S'), "메시지": parts[1].strip()})
                    df_log = pd.DataFrame(reversed(log_entries))
                    st.dataframe(df_log, width='stretch', hide_index=True)
                    st.write("---")
                    if st.button("🚨 로그 전체 삭제", type="primary"):
                        if os.path.exists(LOG_FILE):
                            os.remove(LOG_FILE)
                            st.success("✅ 모든 로그 기록이 삭제되었습니다. 목록이 곧 갱신됩니다.")
                            # [개선] 즉시 rerun 대신 자동 새로고침에 맡겨 안정성 확보
                else: st.info("👀 로그 파일은 비어있습니다.")
            except Exception as e: st.error(f"로그 파일을 읽는 중 오류가 발생했습니다: {e}")
        else: st.info("👍 아직 감지된 이벤트가 없어 로그 파일이 생성되지 않았습니다.")

    def run(self):
        st.set_page_config(page_title="PORTY Sensor Dashboard", layout="wide")
        
        # [변경] 안정적인 자동 새로고침 컴포넌트 사용
        st_autorefresh(interval=2000, limit=None)
        
        self._start_mqtt_thread_once()
        self._load_initial_data()
        self._process_mqtt_queue()
        
        self._handle_sidebar()
        self._render_page()
        
        # [변경] 충돌을 유발하는 수동 새로고침 로직 삭제

if __name__ == "__main__":
    app = SensorDashboard()
    app.run()
