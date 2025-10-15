import streamlit as st
import streamlit.components.v1 as components
import os

# -----------------------------------------------------------------------------
# 1. 외부 HTML 파일을 읽어오는 부분
# -----------------------------------------------------------------------------
try:
    with open('sound_component.html', 'r', encoding='utf-8') as f:
        sound_component_html = f.read()
except FileNotFoundError:
    st.error("오류: `sound_component.html` 파일을 찾을 수 없습니다. `sound_app.py`와 같은 폴더에 있는지 확인하세요.")
    st.stop()

# -----------------------------------------------------------------------------
# 2. Streamlit 앱 UI 구성
# -----------------------------------------------------------------------------
st.set_page_config(page_title="외부 파일 사운드 테스트", layout="centered")
st.title("🔊 외부 HTML 파일을 이용한 사운드 테스트")
st.markdown("---")

if 'sound_activated' not in st.session_state:
    st.session_state.sound_activated = False

# 상태에 따라 UI를 다르게 표시
if not st.session_state.sound_activated:
    # 1. 활성화 전: 활성화 버튼이 포함된 컴포넌트 렌더링
    st.info("👇 아래의 **'알림음 활성화'** 버튼을 먼저 클릭해주세요.")
    component_return_value = components.html(sound_component_html, height=100)
    
    if isinstance(component_return_value, dict) and component_return_value.get('activated'):
        st.session_state.sound_activated = True
        st.experimental_rerun()
else:
    # 2. 활성화 후: 테스트 버튼들과 보이지 않는 리스너 컴포넌트 렌더링
    st.success("✅ 사운드가 활성화되었습니다! 이제 아래 버튼으로 테스트하세요.")
    col1, col2 = st.columns(2)

    if col1.button("🔥 화재 경보음 재생", use_container_width=True, type="primary"):
        # JavaScript에 'PLAY_SOUND' 메시지 전송
        components.html("""
            <script>
                window.parent.postMessage({type: 'PLAY_SOUND', soundType: 'fire'}, '*');
            </script>
        """, height=0)

    if col2.button("⚠️ 주의음 재생", use_container_width=True):
        components.html("""
            <script>
                window.parent.postMessage({type: 'PLAY_SOUND', soundType: 'safety'}, '*');
            </script>
        """, height=0)

    # 소리 재생 명령을 계속 듣기 위해 보이지 않는 컴포넌트를 렌더링
    components.html(sound_component_html, height=0)
