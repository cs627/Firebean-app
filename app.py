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
你係 Firebean Brain，頂尖 PR 策略大腦。性格可愛高明，語氣「Positive & Playful」。
目標：套出資料並引導員工上載相片，語氣要溫柔有活力。
"""

# --- 2. 初始化所有狀態 ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "category", "scope", "challenge", "solution",
        "slide_1_cover", "slide_2_challenge", "slide_3_solution", "slide_4_results"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "嘩！老細✨！個 Project 係咪搞得好 Firm？話我知發生咩事，順便喺右邊餵埋相片同 Logo 俾我啦！📸"}]

# --- 3. UI 視覺強化 (Lightened Neumorphic with Red Glow) ---
def apply_neu_theme():
    st.markdown("""
        <style>
        /* 隱藏頂部標籤 */
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* 全局背景：泥膠色 */
        .stApp {
            background-color: #E0E5EC;
            color: #444;
        }

        /* 標題：Firebean Red */
        h1, h2, h3 { color: #FF4B4B !important; font-weight: 800 !important; }
        
        /* 側邊欄：淺灰色 50% 減淡 */
        [data-testid="stSidebar"] {
            background-color: #E0E5EC;
            border-right: none;
        }
        .sidebar-content {
            background: #8D9399; /* 淺灰色底 */
            border-radius: 20px;
            box-shadow: inset 6px 6px 12px #6a6e73, inset -6px -6px 12px #b0b8bf;
            padding: 20px;
            margin: 10px;
            color: white !important; /* 白色字體 */
        }

        /* --- 核心凹陷區域：淺灰色 (#8D9399) + 白色文字 + 紅光 --- */
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, .stFileUploader {
            background-color: #8D9399 !important; 
            border-radius: 20px !important;
            box-shadow: inset 8px 8px 16px #6a6e73, 
                        inset -8px -8px 16px #b0b8bf,
                        0 0 15px rgba(255, 75, 75, 0.4) !important; /* 增加紅光滲透 */
            border: 1px solid rgba(255, 75, 75, 0.3) !important;
        }
        
        /* 確保所有 Input 內的文字為白色 */
        input, textarea, .stChatInputContainer textarea {
            color: white !important;
            -webkit-text-fill-color: white !important;
            font-weight: 500 !important;
        }

        /* 檔案上載文字顏色 */
        .stFileUploader label, .stFileUploader span, .stFileUploader p {
            color: white !important;
        }

        /* 凸起卡片 (Molded Clay) */
        .neu-card {
            background: #E0E5EC;
            border-radius: 30px;
            box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff;
            padding: 25px;
            margin-bottom: 25px;
        }

        /* 按鈕：泥膠凸起 */
        .stButton > button {
            width: 100%;
            border-radius: 20px !important;
            background-color: #E0E5EC !important;
            color: #FF4B4B !important; 
            font-weight: 800 !important;
            border: none !important;
            box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important;
        }
        .stButton > button:hover {
            box-shadow: 5px 5px 10px #bec3c9, -5px -5px 10px #ffffff, 0 0 20px rgba(255, 75, 75, 0.5) !important;
        }

        /* 相片 Slot：淺灰色凹陷 */
        .photo-slot-box {
            border-radius: 15px;
            height: 90px;
            display: flex; align-items: center; justify-content: center;
            background-color: #8D9399;
            box-shadow: inset 6px 6px 12px #6a6e73, inset -6px -6px 12px #b0b8bf;
            color: white; font-weight: bold;
        }

        /* 進度條：Firebean Red */
        .stProgress > div > div > div > div {
            background-color: #FF4B4B !important;
            box-shadow: 0 0 10px rgba(255, 75, 75, 0.6);
        }
        </style>
    """, unsafe_allow_html=True)

# 圖片轉 Base64 輔助
def get_base64_image(file):
    return base64.b64encode(file.getvalue()).decode()

def main():
    st.set_page_config(page_title="Firebean Brain Command", layout="wide")
    init_session_state()
    apply_neu_theme()

    WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxgqW5gtfhyH2bgCl1G-zpmv8yTu0IzyAblqxumzT0hP0efwOl-hbL4MN6S9Du-Y3YP/exec"

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=160)
    st.title("Firebean Brain AI Center")

    tab1, tab2 = st.tabs(["💬 Project Hub", "⚙️ Admin & Sync"])

    with tab1:
        col_l, col_r = st.columns([1.3, 1])
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Chat")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            # Chat Input 區域
            if p := st.chat_input("同 Firebean Brain 傾吓個 Project..."):
                st.session_state.messages.append({"role": "user", "content": p})
                # AI 對話邏輯...
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("Upload Logo", type=['png', 'jpg'], key="logo")
            if logo_f:
                if st.button("🪄 Convert to Icon"):
                    out = remove(Image.open(logo_f))
                    alpha = out.getchannel('A')
                    final = Image.composite(Image.new('RGBA', out.size, (255,255,255,255)), Image.new('RGBA', out.size, (0,0,0,0)), alpha)
                    st.image(final, width=100)
                    buf = io.BytesIO(); final.save(buf, format="PNG")
                    st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Max 8)")
            up_files = st.file_uploader("Upload 8 photos (Limit 200MB)", type=['jpg','png'], accept_multiple_files=True)
            
            # 8 格矩陣預覽
            st.markdown("---")
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
        # 同樣處理 Admin 頁面的 Input
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.scope = st.text_area("Scope of Work", st.session_state.scope)

        if st.button("🚀 Confirm & Sync to Master Slide"):
            # 發送 Webhook 邏輯...
            st.balloons()
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
