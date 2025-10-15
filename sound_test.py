import streamlit as st
import streamlit.components.v1 as components

# --- HTML 파일을 읽어옴 ---
try:
    with open('sound_controller.html', 'r', encoding='utf-8') as f:
        sound_controller_html_template = f.read()
except FileNotFoundError:
    st.error("오류: `sound_controller.html` 파일을 찾을 수 없습니다. `sound_app.py`와 같은 폴더에 있는지 확인하세요.")
    st.stop()

# --- Streamlit 앱 UI ---
st.set_page_config(page_title="최종 사운드 테스트", layout="centered")
st.title("🔊 최종 사운드 테스트 (안정화 버전)")
st.markdown("---")

# 세션 상태 초기화
if 'sound_activated' not in st.session_state:
    st.session_state.sound_activated = False
if 'sound_to_play' not in st.session_state:
    st.session_state.sound_to_play = "none"

# ⭐️핵심: 재생할 소리가 있다면 HTML에 데이터로 삽입합니다.
html_to_render = sound_controller_html_template.replace(
    'data-sound-to-play="none"',
    f'data-sound-to-play="{st.session_state.sound_to_play}"'
)

# 컴포넌트를 렌더링하고, JS로부터 오는 값을 받습니다.
component_return_value = components.html(html_to_render, height=0)

# JS에서 활성화 신호를 받으면 상태 업데이트
if isinstance(component_return_value, dict) and component_return_value.get('activated'):
    if not st.session_state.sound_activated:
        st.session_state.sound_activated = True
        st.rerun()

# 소리 재생 명령을 보낸 후에는 상태를 초기화하여 반복 재생 방지
if st.session_state.sound_to_play != "none":
    st.session_state.sound_to_play = "none"

# --- UI 버튼 구성 ---
if not st.session_state.sound_activated:
    st.info("👇 아래 버튼을 클릭하여 소리 재생을 허용해주세요.")
    if st.button("🔔 알림음 활성화 (최초 1회 클릭)", use_container_width=True):
        # 'activate' 명령을 HTML에 전달
        st.session_state.sound_to_play = "activate"
        st.rerun()
else:
    st.success("✅ 사운드가 활성화되었습니다! 이제 아래 버튼으로 테스트하세요.")
    col1, col2 = st.columns(2)

    if col1.button("🔥 화재 경보음 재생", use_container_width=True, type="primary"):
        # 'fire' 명령을 HTML에 전달
        st.session_state.sound_to_play = "fire"
        st.rerun()

    if col2.button("⚠️ 주의음 재생", use_container_width=True):
        # 'safety' 명령을 HTML에 전달
        st.session_state.sound_to_play = "safety"
        st.rerun()
