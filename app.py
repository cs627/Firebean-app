import streamlit as st
import google.generativeai as genai
import requests
import json
import io
import base64
from PIL import Image
from rembg import remove

# --- 1. 核心性格與語音轉錄指令 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，頂尖 PR 策略大腦。
性格：可愛高明、Positive & Playful。
語言：Canto-English (Vibe, Firm, Chill)。
語音轉錄任務：如果收到音檔轉錄請求，請精確還原廣東話口語文字，並保留語氣。
"""

# --- 2. 初始化所有狀態 ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "category", "scope", "challenge", "solution", "logo_b64"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "嘩！老細✨！今日搞完 Event 係咪攰到唔想打字？你可以直接㩒下面個咪同我講錄音，我會幫你聽清楚晒！📸"}]

# --- 3. UI 視覺強化 (Speech Bubbles + Neumorphic) ---
def apply_neu_theme():
    st.markdown("""
        <style>
        header {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #444; }

        /* --- 對話框樣式 --- */
        [data-testid="stChatMessage"] {
            background-color: transparent !important;
            border: none !important;
        }

        /* AI 回覆：凸起泥膠塊 */
        .st-emotion-cache-janbn0 { 
            background: #E0E5EC !important;
            border-radius: 20px 20px 20px 5px !important;
            box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important;
            padding: 15px !important;
            border: 1px solid rgba(255, 75, 75, 0.2) !important;
        }

        /* User 對話：凹陷槽位 */
        .st-emotion-cache-1c7n2ri {
            background: #E0E5EC !important;
            border-radius: 20px 20px 5px 20px !important;
            box-shadow: inset 6px 6px 12px #bec3c9, inset -6px -6px 12px #ffffff !important;
            padding: 15px !important;
            border: 1px solid rgba(255, 75, 75, 0.1) !important;
        }

        /* 文字顏色確保清晰 */
        span, p, .stMarkdown { color: #2D3436 !important; font-weight: 500; }

        /* 凸起卡片 (Molded Clay) */
        .neu-card {
            background: #E0E5EC;
            border-radius: 30px;
            box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff;
            padding: 25px;
            margin-bottom: 25px;
        }

        /* 錄音組件樣式優化 */
        [data-testid="stAudioInput"] {
            background-color: #E0E5EC !important;
            border-radius: 30px !important;
            box-shadow: 8px 8px 16px #bec3c9, -8px -8px 16px #ffffff, 0 0 10px rgba(255, 75, 75, 0.3) !important;
            border: none !important;
            padding: 10px !important;
        }

        /* 按鈕：泥膠凸起 */
        .stButton > button {
            width: 100%; border-radius: 20px !important;
            background-color: #E0E5EC !important;
            color: #FF4B4B !important; font-weight: 800 !important;
            box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important;
        }
        </style>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()
    apply_neu_theme()

    # API 設定
    api_key = "AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=160)
    
    tab1, tab2 = st.tabs(["💬 Project Brain Hub", "⚙️ Admin & Sync"])

    with tab1:
        col_l, col_r = st.columns([1.3, 1])
        
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean Brain Assistant")
            
            # 對話泡泡顯示
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            # --- 語音錄音與轉錄功能 ---
            st.markdown("---")
            audio_input = st.audio_input("🎤 撳住錄音話我知 Project 詳情...")
            
            if audio_input:
                with st.spinner("聽緊你講咩... AI 轉錄中..."):
                    # 將音檔直接發送給 Gemini 處理
                    audio_bytes = audio_input.read()
                    response = model.generate_content([
                        "請精確轉錄這段廣東話錄音，並分析其中的 Project 詳情 (Client, Venue, Challenge, Result)。",
                        {"mime_type": "audio/wav", "data": audio_bytes}
                    ])
                    transcribed_text = response.text
                    
                    # 將轉錄結果加入對話紀錄
                    st.session_state.messages.append({"role": "user", "content": f"🎤 [語音轉錄]: {transcribed_text}"})
                    st.rerun()

            # 文字輸入 (備用)
            if p := st.chat_input("打字傾計亦得..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    response = model.generate_content(p)
                    st.write(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            # Logo Studio 模組 (維持之前的功能)
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("Upload Logo", type=['png', 'jpg'], key="logo")
            if logo_f:
                if st.button("🪄 Convert to White Icon"):
                    img = Image.open(logo_f)
                    out = remove(img)
                    alpha = out.getchannel('A')
                    final = Image.composite(Image.new('RGBA', out.size, (255,255,255,255)), Image.new('RGBA', out.size, (0,0,0,0)), alpha)
                    st.image(final, width=120)
                    buf = io.BytesIO(); final.save(buf, format="PNG")
                    st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

            # 8 格 Gallery
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            up_files = st.file_uploader("Upload 8 photos", type=['jpg','png'], accept_multiple_files=True)
            st.markdown('---')
            g1, g2, g3, g4 = st.columns(4); g5, g6, g7, g8 = st.columns(4)
            slots = [g1, g2, g3, g4, g5, g6, g7, g8]
            for i in range(8):
                with slots[i]:
                    if up_files and i < len(up_files):
                        st.image(up_files[i], use_column_width=True)
                    else:
                        st.markdown(f'<div class="photo-slot-box">{i+1}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Final Review")
        # 資料同步邏輯...
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
