import streamlit as st
import google.generativeai as genai
import requests
import json
import io
import base64
from PIL import Image
from rembg import remove

# --- 1. 核心性格與指令 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，頂尖 PR 策略大腦。性格可愛高明。
目標：透過對話套出 Client, Project, Venue, Challenge, Result 等資料。
語音轉錄任務：請精確還原廣東話口語文字。
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
        st.session_state.messages = [{"role": "assistant", "content": "嘩！老細✨！今日個 Project 係咪搞得好 Firm？話我知發生咩事，順便喺右邊餵埋相片同 Logo 俾我啦！📸"}]

# --- 3. UI 視覺強化 (Neumorphic + Energy Bar + Centered Logo) ---
def apply_neu_theme():
    # 計算進度百分比 (基於 8 個核心欄位)
    track_fields = ["client_name", "project_name", "event_date", "venue", "category", "scope", "challenge", "solution"]
    filled = sum(1 for f in track_fields if st.session_state[f])
    progress_percent = int((filled / len(track_fields)) * 100)

    st.markdown(f"""
        <style>
        header {{visibility: hidden;}}
        .stApp {{ background-color: #E0E5EC; color: #2D3436; }}

        /* --- 頂部能量進度條 (Energy Bar) --- */
        .energy-container {{
            width: 100%;
            background: #E0E5EC;
            padding: 10px 20px;
            position: sticky;
            top: 0;
            z-index: 999;
            border-bottom: 1px solid rgba(255,255,255,0.3);
        }}
        .energy-bar-bg {{
            height: 12px;
            background: #E0E5EC;
            border-radius: 10px;
            box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff;
            overflow: hidden;
            position: relative;
        }}
        .energy-bar-fill {{
            height: 100%;
            width: {progress_percent}%;
            background: linear-gradient(90deg, #FF4B4B, #FF8080);
            box-shadow: 0 0 15px #FF4B4B;
            transition: width 0.8s ease-in-out;
        }}
        .energy-text {{
            font-size: 12px;
            font-weight: bold;
            color: #FF4B4B;
            text-align: right;
            margin-top: 5px;
            text-shadow: 1px 1px 2px #ffffff;
        }}

        /* --- 手機版 Logo 置中 --- */
        [data-testid="stImage"] {{
            display: block;
            margin-left: auto;
            margin-right: auto;
        }

        /* --- 對話框樣式 (Speech Bubbles) --- */
        [data-testid="stChatMessage"] {{ background-color: transparent !important; }}
        /* AI: 凸起 */
        .st-emotion-cache-janbn0 {{ 
            background: #E0E5EC !important;
            border-radius: 20px 20px 20px 5px !important;
            box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important;
            border: 1px solid rgba(255, 75, 75, 0.2) !important;
        }}
        /* User: 凹陷 */
        .st-emotion-cache-1c7n2ri {{
            background: #E0E5EC !important;
            border-radius: 20px 20px 5px 20px !important;
            box-shadow: inset 6px 6px 12px #bec3c9, inset -6px -6px 12px #ffffff !important;
        }}
        span, p, .stMarkdown {{ color: #2D3436 !important; font-weight: 500; }}

        /* --- 修正深灰色 Box (不再是黑色) --- */
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, [data-testid="stAudioInput"], .stFileUploader {{
            background-color: #BEC3C9 !important; /* 淺 50% 灰色 */
            border-radius: 20px !important;
            box-shadow: inset 6px 6px 12px #9da3ab, inset -6px -6px 12px #ffffff !important;
            border: 1px solid rgba(255, 75, 75, 0.3) !important;
        }
        input, textarea, .stChatInputContainer textarea {{
            color: white !important;
            -webkit-text-fill-color: white !important;
        }
        .stFileUploader label, .stFileUploader span {{ color: white !important; }}

        /* 凸起卡片 */
        .neu-card {{
            background: #E0E5EC;
            border-radius: 30px;
            box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff;
            padding: 25px;
            margin-bottom: 25px;
        }

        /* 按鈕：泥膠凸起 */
        .stButton > button {{
            width: 100%; border-radius: 20px !important;
            background-color: #E0E5EC !important;
            color: #FF4B4B !important; font-weight: 800 !important;
            box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important;
        }
        </style>

        <div class="energy-container">
            <div class="energy-bar-bg"><div class="energy-bar-fill"></div></div>
            <div class="energy-text">BRAIN ENERGY: {progress_percent}%</div>
        </div>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain Command", layout="wide")
    init_session_state()
    apply_neu_theme()

    # API 設定
    api_key = "AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)

    # Logo (已加 CSS 置中)
    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)

    tab1, tab2 = st.tabs(["💬 Brain Hub", "⚙️ Admin & Sync"])

    with tab1:
        col_chat, col_assets = st.columns([1.3, 1])
        
        with col_chat:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean Brain Assistant")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            st.markdown("---")
            # 語音錄音
            audio_input = st.audio_input("🎤 撳住錄音話我知 Project 詳情...")
            if audio_input:
                with st.spinner("聽緊你講咩..."):
                    res = model.generate_content(["請精確轉錄廣東話錄音並分析 Project 資料。", {"mime_type": "audio/wav", "data": audio_input.read()}])
                    st.session_state.messages.append({"role": "user", "content": f"🎤 [錄音轉錄]: {res.text}"})
                    st.rerun()

            if p := st.chat_input("打字傾計亦得..."):
                st.session_state.messages.append({"role": "user", "content": p})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_assets:
            # Logo Studio
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("Upload Logo", type=['png', 'jpg'], key="logo")
            if logo_f and st.button("🪄 Convert to White Icon"):
                out = remove(Image.open(logo_f))
                final = Image.composite(Image.new('RGBA', out.size, (255,255,255,255)), Image.new('RGBA', out.size, (0,0,0,0)), out.getchannel('A'))
                st.image(final, width=120)
                st.session_state['logo_b64'] = base64.b64encode(io.BytesIO().getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

            # Gallery (8格)
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            up_files = st.file_uploader("Upload 8 photos", type=['jpg','png'], accept_multiple_files=True)
            st.markdown('---')
            g1, g2, g3, g4 = st.columns(4); g5, g6, g7, g8 = st.columns(4)
            slots = [g1, g2, g3, g4, g5, g6, g7, g8]
            for i in range(8):
                with slots[i]:
                    if up_files and i < len(up_files): st.image(up_files[i], use_column_width=True)
                    else: st.markdown(f'<div style="height:80px; background:#E0E5EC; border-radius:10px; box-shadow:inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; display:flex; align-items:center; justify-content:center; color:#aaa; font-size:10px;">Slot {i+1}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Final Review")
        # 顯示所有欄位以便確認
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        st.session_state.scope = st.text_area("Scope", st.session_state.scope)
        if st.button("🚀 Confirm & Sync to Master Slide"):
            st.balloons()
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
