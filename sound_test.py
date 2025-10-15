import streamlit as st
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. 모든 HTML과 JavaScript 로직을 하나의 문자열로 통합
# -----------------------------------------------------------------------------
# 이 컴포넌트는 두 가지 역할을 합니다:
# - 최초에 '알림음 활성화' 버튼을 표시합니다.
# - 한번 활성화되면, Python에서 보내는 'play-sound' 이벤트를 계속 듣고 있다가 소리를 재생합니다.
# -----------------------------------------------------------------------------
sound_component_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Sound Component</title>
</head>
<body>
    <div id="activation-div">
        <p>알림음을 사용하려면 아래 버튼을 눌러주세요.</p>
        <button 
            id="activate-sound-btn"
            style="width: 100%; padding: 8px; border-radius: 8px; border: 1px solid transparent; background-color: #4CAF50; color: white; font-size: 16px; cursor: pointer;"
        >
            🔔 알림음 활성화 (최초 1회 클릭)
        </button>
    </div>

    <script>
        // --- 오디오 로직 ---
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();

        // 1. 오디오 컨텍스트를 활성화하는 함수
        async function initAudio() {
            if (audioContext.state === 'suspended') {
                console.log("AudioContext is suspended. Resuming...");
                await audioContext.resume();
                console.log("AudioContext has been resumed by user interaction.");
            }
        }
        
        // 2. 실제 소리를 재생하는 함수
        function playSound(type) {
            if (audioContext.state !== 'running') {
                console.warn("AudioContext is not running. Sound playback aborted.");
                return;
            }

            if (type === 'fire') {
                // ... 화재 경보음 로직 ...
                const masterGain = audioContext.createGain();
                masterGain.gain.setValueAtTime(0.3, audioContext.currentTime);
                masterGain.connect(audioContext.destination);
                let highTone = 800, lowTone = 450, duration = 0.15, startTime = audioContext.currentTime;
                for (let i = 0; i < 4; i++) {
                    const osc = audioContext.createOscillator();
                    osc.type = 'sawtooth';
                    osc.frequency.setValueAtTime(i % 2 === 0 ? highTone : lowTone, startTime + i * duration);
                    osc.connect(masterGain);
                    osc.start(startTime + i * duration);
                    osc.stop(startTime + (i + 1) * duration);
                }
            } else if (type === 'safety') {
                // ... 주의음 로직 ...
                function createBeep(startTime) {
                    const osc = audioContext.createOscillator();
                    const gainNode = audioContext.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(880, startTime);
                    gainNode.gain.setValueAtTime(0.4, startTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.001, startTime + 0.2);
                    osc.connect(gainNode);
                    gainNode.connect(audioContext.destination);
                    osc.start(startTime);
                    osc.stop(startTime + 0.2);
                }
                createBeep(audioContext.currentTime);
                createBeep(audioContext.currentTime + 0.25);
            }
        }

        // --- Streamlit과의 통신 로직 ---

        const activationButton = document.getElementById('activate-sound-btn');
        const activationDiv = document.getElementById('activation-div');
        
        // 3. 활성화 버튼 클릭 이벤트
        activationButton.onclick = async () => {
            await initAudio(); // 오디오 활성화!
            
            // 버튼이 클릭되었다는 사실을 Python에 알림
            window.parent.Streamlit.setComponentValue({ activated: true });
            
            // 버튼 숨기기
            activationDiv.style.display = 'none';
        };

        // 4. Python으로부터 소리 재생 명령을 받는 리스너
        window.addEventListener('message', event => {
            if (event.data.type === 'PLAY_SOUND') {
                playSound(event.data.soundType);
            }
        });

    </script>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# 2. Streamlit 앱 UI 구성
# -----------------------------------------------------------------------------
st.set_page_config(page_title="최종 사운드 테스트", layout="centered")
st.title("🔊 최종 Streamlit 사운드 테스트")
st.markdown("---")

# 세션 상태 초기화
if 'sound_activated' not in st.session_state:
    st.session_state.sound_activated = False

st.header("테스트 방법")
if not st.session_state.sound_activated:
    st.info("👇 아래의 **'알림음 활성화'** 버튼을 먼저 클릭해주세요.")
else:
    st.success("✅ 사운드가 활성화되었습니다! 이제 아래 버튼으로 테스트하세요.")

# 컴포넌트 렌더링 및 Python-JS 통신
component_return_value = components.html(sound_component_html, height=100)

if component_return_value and component_return_value.get('activated'):
    st.session_state.sound_activated = True
    st.rerun()

# 사운드가 활성화된 후에만 테스트 버튼을 보여줌
if st.session_state.sound_activated:
    col1, col2 = st.columns(2)

    if col1.button("🔥 화재 경보음 재생", use_container_width=True, type="primary"):
        # JavaScript에 'PLAY_SOUND' 메시지 전송
        st.components.v1.html("""
            <script>
                window.parent.postMessage({type: 'PLAY_SOUND', soundType: 'fire'}, '*');
            </script>
        """, height=0)

    if col2.button("⚠️ 주의음 재생", use_container_width=True):
        # JavaScript에 'PLAY_SOUND' 메시지 전송
        st.components.v1.html("""
            <script>
                window.parent.postMessage({type: 'PLAY_SOUND', soundType: 'safety'}, '*');
            </script>
        """, height=0)
