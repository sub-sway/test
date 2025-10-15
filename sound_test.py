import streamlit as st
import streamlit.components.v1 as components

# --- HTML 파일을 읽어옴 ---
try:
    with open('sound_controller.html', 'r', encoding='utf-8') as f:
        sound_controller_html = f.read()
except FileNotFoundError:
    st.error("오류: `sound_controller.html` 파일을 찾을 수 없습니다. `sound_app.py`와 같은 폴더에 있는지 확인하세요.")
    st.stop()

# --- Streamlit 앱 UI ---
st.set_page_config(page_title="최종 사운드 테스트", layout="centered")
st.title("🔊 최종 사운드 테스트 (안정화 버전)")
st.markdown("---")

# 1. 보이지 않는 오디오 컨트롤러를 앱에 항상 삽입
# 이 컴포넌트가 Python의 명령을 기다리는 역할을 함
components.html(sound_controller_html, height=0)

# 세션 상태 초기화
if 'sound_activated' not in st.session_state:
    st.session_state.sound_activated = False

# 2. 상태에 따라 UI를 분기하여 표시
if not st.session_state.sound_activated:
    # 활성화 전 UI
    st.info("👇 아래 버튼을 클릭하여 소리 재생을 허용해주세요.")
    
    if st.button("🔔 알림음 활성화 (최초 1회 클릭)", use_container_width=True):
        # 버튼 클릭 시, JavaScript에 'INIT_AUDIO' 명령 전송
        components.html("""
            <script>
                window.parent.postMessage({type: 'INIT_AUDIO'}, '*');
            </script>
        """, height=0)
        # 상태를 '활성화됨'으로 변경하고, Streamlit이 자동으로 UI를 다시 그리게 함
        st.session_state.sound_activated = True
        st.experimental_rerun()
else:
    # 활성화 후 UI
    st.success("✅ 사운드가 활성화되었습니다! 이제 아래 버튼으로 테스트하세요.")
    col1, col2 = st.columns(2)

    if col1.button("🔥 화재 경보음 재생", use_container_width=True, type="primary"):
        # JavaScript에 'PLAY_SOUND' (fire) 명령 전송
        components.html("""
            <script>
                window.parent.postMessage({type: 'PLAY_SOUND', soundType: 'fire'}, '*');
            </script>
        """, height=0)

    if col2.button("⚠️ 주의음 재생", use_container_width=True):
        # JavaScript에 'PLAY_SOUND' (safety) 명령 전송
        components.html("""
            <script>
                window.parent.postMessage({type: 'PLAY_SOUND', soundType: 'safety'}, '*');
            </script>
        """, height=0)
