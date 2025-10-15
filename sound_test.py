import streamlit as st
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. 모든 HTML과 JavaScript 로직을 하나의 문자열로 통합
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
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();

        async function initAudio() {
            if (audioContext.state === 'suspended') {
                console.log("AudioContext is suspended. Resuming...");
                await audioContext.resume();
                console.log("AudioContext has been resumed by user interaction.");
            }
        }
        
        function playSound(type) {
            if (audioContext.state !== 'running') {
                console.warn("AudioContext is not running. Sound playback aborted.");
                return;
            }

            if (type === 'fire') {
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

        const activationButton = document.getElementById('activate-sound-btn');
        const activationDiv = document.getElementById('activation-div');
        
        activationButton.onclick = async () => {
            await initAudio();
            window.parent.Streamlit.setComponentValue({ activated: true });
            activationDiv.style.display = 'none';
        };

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

if 'sound_activated' not in st.session_state:
    st.session_state.sound_activated = False

st.header("테스트 방법")
if not st.session_state.sound_activated:
    st.info("👇 아래의 **'알림음 활성화'** 버튼을 먼저 클릭해주세요.")
else:
    st.success("✅ 사운드가 활성화되었습니다! 이제 아래 버튼으로 테스트하세요.")

component_return_value = components.html(sound_component_html, height=100)

# ⭐️⭐️⭐️ 여기가 수정된 핵심 부분입니다! ⭐️⭐️⭐️
# 'component_return_value'가 딕셔너리인지 먼저 확인하여 오류를 방지합니다.
if isinstance(component_return_value, dict) and component_return_value.get('activated'):
    if not st.session_state.sound_activated:
        st.session_state.sound_activated = True
        st.rerun()

if st.session_state.sound_activated:
    col1, col2 = st.columns(2)

    if col1.button("🔥 화재 경보음 재생", use_container_width=True, type="primary"):
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
