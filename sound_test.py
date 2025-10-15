import streamlit as st

def render_sidebar():
    """사이드바의 설정 옵션을 렌더링합니다."""
    with st.sidebar:
        st.header("⚙️ 설정")
        st.subheader("알림음 설정")

        # sound_primed 상태가 없으면 초기화
        if 'sound_primed' not in st.session_state:
            st.session_state.sound_primed = False

        # sound_enabled 상태가 없으면 초기화
        if 'sound_enabled' not in st.session_state:
            st.session_state.sound_enabled = False

        # 1. 최초 오디오 활성화 버튼
        if not st.session_state.sound_primed:
            st.write("알림음을 사용하려면 아래 버튼을 눌러주세요.")
            
            # HTML 버튼을 사용하여 JS 함수(initAudio)를 직접 호출
            # 버튼 클릭 시 Streamlit의 세션 상태를 변경하기 위해 setComponentValue 사용
            if st.components.v1.html("""
                <script>
                    async function activateAudio() {
                        // initAudio 함수는 아래 handle_audio_playback 함수에 정의되어 있음
                        // window.parent.parent 를 통해 Streamlit의 메인 window 객체에 접근
                        await window.parent.parent.initAudio();
                        
                        // 버튼이 클릭되었다는 값을 Streamlit으로 전달
                        const st = window.parent.parent.Streamlit;
                        st.setComponentValue(true);
                    }
                </script>
                <button 
                    onclick="activateAudio()"
                    style="width: 100%; padding: 8px; border-radius: 8px; border: 1px solid transparent; background-color: #4CAF50; color: white; font-size: 16px; cursor: pointer;"
                >
                    🔔 알림음 활성화 (최초 1회 클릭)
                </button>
                """, height=50):
                st.session_state.sound_primed = True
                st.session_state.sound_enabled = True
                st.rerun() # 상태 변경 후 UI 갱신

        # 2. 활성화 이후의 토글 스위치
        else:
            st.session_state.sound_enabled = st.toggle(
                "알림음 활성화/비활성화", value=st.session_state.sound_enabled
            )

        # 3. 현재 상태 표시
        if st.session_state.sound_primed:
            if st.session_state.sound_enabled:
                st.success("알림음 활성화 상태")
            else:
                st.warning("알림음 비활성화 상태")

def handle_audio_playback():
    """경고음 재생을 처리하는 JS 코드를 삽입하고, 트리거에 따라 실행합니다."""
    
    # 1. 브라우저에 오디오 초기화 및 소리 생성 JavaScript 코드 주입
    st.html("""
        <script>
            // 오디오 컨텍스트를 window 객체에 저장하여 재사용
            if (!window.audioContext) {
                window.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }

            // 오디오 컨텍스트를 활성화하는 함수 (사용자 클릭으로 호출되어야 함)
            async function initAudio() {
                if (window.audioContext.state === 'suspended') {
                    console.log("AudioContext is suspended. Resuming...");
                    await window.audioContext.resume();
                    console.log("AudioContext resumed successfully.");
                }
            }
            // Streamlit 외부(st.html 버튼)에서도 호출 가능하도록 window에 등록
            window.parent.parent.initAudio = initAudio;

            // 소리 재생 메인 함수
            function playSound(type) {
                if (window.audioContext.state !== 'running') {
                    console.warn("AudioContext is not running. Sound playback aborted. Please click the activation button first.");
                    return;
                }
                
                if (type === 'fire') {
                    const masterGain = window.audioContext.createGain();
                    masterGain.gain.setValueAtTime(0.3, window.audioContext.currentTime);
                    masterGain.connect(window.audioContext.destination);
                    let highTone = 800, lowTone = 450, duration = 0.15, startTime = window.audioContext.currentTime;
                    for (let i = 0; i < 4; i++) {
                        const osc = window.audioContext.createOscillator();
                        osc.type = 'sawtooth';
                        osc.frequency.setValueAtTime(i % 2 === 0 ? highTone : lowTone, startTime + i * duration);
                        osc.connect(masterGain);
                        osc.start(startTime + i * duration);
                        osc.stop(startTime + (i + 1) * duration);
                    }
                } else if (type === 'safety') {
                    function createBeep(startTime) {
                        const osc = window.audioContext.createOscillator();
                        const gainNode = window.audioContext.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(880, startTime);
                        gainNode.gain.setValueAtTime(0.4, startTime);
                        gainNode.gain.exponentialRampToValueAtTime(0.001, startTime + 0.2);
                        osc.connect(gainNode);
                        gainNode.connect(window.audioContext.destination);
                        osc.start(startTime);
                        osc.stop(startTime + 0.2);
                    }
                    createBeep(window.audioContext.currentTime);
                    createBeep(window.audioContext.currentTime + 0.25);
                }
            }
        </script>
    """)

    # 2. 파이썬에서 상태를 확인하고, 위에서 만든 JavaScript 함수를 호출
    if 'play_sound_trigger' in st.session_state and st.session_state.play_sound_trigger:
        trigger = st.session_state.play_sound_trigger
        st.html(f"<script>playSound('{trigger}');</script>")
        # 트리거를 사용한 후에는 반드시 초기화하여 반복 재생을 방지
        st.session_state.play_sound_trigger = None

# --- 메인 앱 실행 ---

st.set_page_config(page_title="사운드 테스트", layout="centered")
st.title("🔊 Streamlit Web Audio API 테스트")
st.markdown("---")

# 사이드바 UI 렌더링
render_sidebar()

st.header("테스트 방법")
st.info("""
1.  왼쪽 사이드바에서 **'🔔 알림음 활성화'** 버튼을 클릭하세요.
2.  사이드바에 "알림음 활성화 상태" 메시지가 표시되면 준비 완료입니다.
3.  아래의 두 버튼을 눌러 소리가 정상적으로 나는지 확인하세요.
""")

col1, col2 = st.columns(2)

# 파이썬 버튼 클릭 시 st.session_state.play_sound_trigger 값을 변경
if col1.button("🔥 화재 경보음 재생", use_container_width=True, type="primary"):
    if st.session_state.sound_enabled:
        st.session_state.play_sound_trigger = 'fire'
    else:
        st.warning("먼저 사이드바에서 알림음을 활성화해주세요.")

if col2.button("⚠️ 주의음 재생", use_container_width=True):
    if st.session_state.sound_enabled:
        st.session_state.play_sound_trigger = 'safety'
    else:
        st.warning("먼저 사이드바에서 알림음을 활성화해주세요.")

# 실제 소리를 재생하는 로직 호출
handle_audio_playback()
