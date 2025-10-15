import streamlit as st

st.set_page_config(layout="centered")

st.title("Streamlit Web Audio API 테스트")

# 1. 소리를 생성하는 JavaScript 코드를 보이지 않게 페이지에 삽입
st.html("""
    <script>
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();

        function playFireAlert() {
            if (!audioContext) return;
            let highTone = 900, lowTone = 500, duration = 0.15, startTime = audioContext.currentTime;
            for (let i = 0; i < 4; i++) {
                const osc = audioContext.createOscillator();
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(i % 2 === 0 ? highTone : lowTone, startTime + i * duration);
                osc.connect(audioContext.destination);
                osc.start(startTime + i * duration);
                osc.stop(startTime + (i + 1) * duration);
            }
        }

        function playSafetyAlert() {
            if (!audioContext) return;
            const osc = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(800, audioContext.currentTime);
            gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.5);
            osc.connect(gainNode);
            gainNode.connect(audioContext.destination);
            osc.start();
            osc.stop(audioContext.currentTime + 0.5);
        }
    </script>
""")

st.info("아래 버튼을 클릭하면 Python이 JavaScript 함수를 호출하여 소리를 재생합니다.")

col1, col2 = st.columns(2)

# 2. 버튼을 누르면 해당 JavaScript 함수를 호출하는 스크립트를 실행
if col1.button("🔥 화재 경보음 재생", use_container_width=True):
    st.html("<script>playFireAlert();</script>")

if col2.button("⚠️ 주의음 재생", use_container_width=True):
    st.html("<script>playSafetyAlert();</script>")
