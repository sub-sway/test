import streamlit as st

st.set_page_config(layout="centered")

st.title("조정된 Web Audio API 사운드 테스트")
st.info("전체적인 볼륨을 낮추고, 주의음을 '삑-삑' 두 번 울리도록 수정했습니다.")

# 1. 수정된 JavaScript 코드를 페이지에 삽입
st.html("""
    <script>
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();

        // 1. 볼륨을 낮춘 화재 경보음
        function playFireAlert() {
            if (!audioContext) return;
            const masterGain = audioContext.createGain(); // 볼륨 조절을 위한 마스터 노드
            masterGain.gain.setValueAtTime(0.3, audioContext.currentTime); // 전체 볼륨을 30%로 설정
            masterGain.connect(audioContext.destination);

            let highTone = 800, lowTone = 450, duration = 0.15, startTime = audioContext.currentTime;

            for (let i = 0; i < 4; i++) { // 4번 반복 (삐-뽀- 삐-뽀-)
                const osc = audioContext.createOscillator();
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(i % 2 === 0 ? highTone : lowTone, startTime + i * duration);
                osc.connect(masterGain); // 마스터 볼륨 노드에 연결
                osc.start(startTime + i * duration);
                osc.stop(startTime + (i + 1) * duration);
            }
        }

        // 2. '삑-삑' 두 번 울려 강조된 주의음
        function playSafetyAlert() {
            if (!audioContext) return;
            
            function createBeep(startTime) {
                const osc = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, startTime); // 주파수를 살짝 높여 주목도 증가
                
                gainNode.gain.setValueAtTime(0.4, startTime); // 볼륨 40%
                // 소리가 갑자기 끊기지 않고 부드럽게 사라지도록 설정
                gainNode.gain.exponentialRampToValueAtTime(0.001, startTime + 0.2); 

                osc.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                osc.start(startTime);
                osc.stop(startTime + 0.2); // 0.2초간 재생
            }

            // 0초 뒤에 첫 번째 삑, 0.25초 뒤에 두 번째 삑 소리 재생
            createBeep(audioContext.currentTime);
            createBeep(audioContext.currentTime + 0.25);
        }
    </script>
""")

col1, col2 = st.columns(2)

# 버튼을 누르면 해당 JavaScript 함수를 호출
if col1.button("🔥 화재 경보음 (조정됨)", use_container_width=True):
    st.html("<script>playFireAlert();</script>")

if col2.button("⚠️ 주의음 (강조됨)", use_container_width=True):
    st.html("<script>playSafetyAlert();</script>")
