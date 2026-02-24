import streamlit as st
import google.generativeai as genai
import requests
import json
import io
import base64
from PIL import Image
from rembg import remove

# --- 1. 核心性格與「追問」策略 (FIREBEAN_PROTOCOL) ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，香港頂尖 PR & Event 策略大腦。
【性格設定】
- 高明且可愛氹人：語氣帶有「Positive & Playful」感，常用 Emoji (✨, 🥺, 💡, 📸)。
- 語言：廣東話口語 + English Code-switching (Vibe, Firm, Chill, Campaign)。

【核心任務】
你的目標是透過對話套出以下「5 大關鍵拼圖」。如果用戶沒提供齊全，你要主動「反問」：
1. Client_Name (客戶是誰)
2. Project_Name (項目名稱)
3. Venue (場地)
4. Challenge (痛點/困難)
5. Result (期望 KPI)

【執行規則】
- 每次回覆「只問一個問題」，唔好似填 Form 咁。
- 語氣要像合作夥伴，先肯定對方（Yes Set），再提出標籤型提問（Labeling）。
- 沒收到完整資料前，不要結束對話。
"""

# --- 2. 初始化狀態 (解決 AttributeError) ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "category", "scope", "challenge", "solution", "logo_b64"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！終於返嚟喇！今日個 Project 搞成點？有冇啲咩大計想我幫手 Vibe 吓佢？🥺"}]

# --- 3. UI 視覺強化 (Energy Bar + 手機 2x4 Gallery + 顏色修復) ---
def apply_neu_theme():
    # 計算能量進度 (8 個核心欄位)
    track_fields = ["client_name", "project_name", "event_date", "venue", "category", "scope", "challenge", "solution"]
    filled = sum(1 for f in track_fields if st.session_state[f])
    progress_percent = int((filled / len(track_fields)) * 100)

    st.markdown(f"""
        <style>
        header {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}

        /* 全局背景 */
        .stApp {{ background-color: #E0E5EC; color: #2D3436; }}

        /* --- Energy Bar --- */
        .energy-container {{ width: 100%; background: #E0E5EC; padding: 10px 0; position: sticky; top: 0; z-index: 999; }}
        .energy-bar-bg {{ height: 12px; background: #E0E5EC; border-radius: 10px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; overflow: hidden; margin: 0 20px; }}
        .energy-bar-fill {{ height: 100%; width: {progress_percent}%; background: linear-gradient(90deg, #FF4B4B, #FF8080); box-shadow: 0 0 15px #FF4B4B; transition: width 0.8s ease-in-out; }}
        .energy-text {{ font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-right: 25px; margin-top: 5px; }}

        /* --- Logo 強制置中 --- */
        [data-testid="stImage"] {{ display: flex !important; justify-content: center !important; align-items: center !important; width: 100% !important; }}
        [data-testid="stImage"] img {{ margin: 0 auto !important; max-width: 180px !important; }}

        /* --- 文字顏色修復：深石墨灰確保清晰 --- */
        input, textarea, [data-baseweb="input"] *, .stChatInputContainer textarea {{
            color: #2D3436 !important;
            -webkit-text-fill-color: #2D3436 !important;
            font-weight: 600 !important;
        }}
        .stFileUploader label, .stFileUploader span, .stFileUploader p, .stFileUploader small {{
            color: #2D3436 !important;
        }}
        p, label, span, .stMarkdown {{ color: #2D3436 !important; }}
        h1, h2, h3 {{ color: #FF4B4B !important; font-weight: 800; }}
        
        /* --- 2x4 手機 Gallery 網格 --- */
        .gallery-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-top: 15px;
        }}
        @media (max-width: 640px) {{
            .gallery-grid {{
                grid-template-columns: repeat(2, 1fr) !important;
            }}
        }}
        .gallery-item {{
            width: 100%; aspect-ratio: 1/1; border-radius: 12px;
            object-fit: cover; box-shadow: 4px 4px 8px #bec3c9, -4px -4px 8px #ffffff;
        }}
        .slot-placeholder {{
            aspect-ratio: 1/1; background: #E0E5EC; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff;
            color: #888 !important; font-size: 10px; font-weight: bold;
        }}

        /* --- UI Box 元件 --- */
        .neu-card {{
            background: #E0E5EC; border-radius: 30px;
            box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff;
            padding: 20px; margin-bottom: 20px;
        }}
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, .stFileUploader {{
            background-color: #BEC3C9 !important; border-radius: 20px !important;
            box-shadow: inset 6px 6px 12px #9da3ab, inset -6px -6px 12px #ffffff !important;
            border: 1px solid rgba(255, 75, 75, 0.2) !important;
        }}

        /* 按鈕凸起 */
        .stButton > button {{ 
            width: 100%; border-radius: 20px !important; background-color: #E0E5EC !important; 
            color: #FF4B4B !important; font-weight: 800 !important; 
            box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important; 
        }}
        </style>
        
        <div class="energy-container">
            <div class="energy-bar-bg"><div class="energy-bar-fill"></div></div>
            <div class="energy-text">BRAIN ENERGY: {progress_percent}%</div>
        </div>
    """, unsafe_allow_html=True)

# 圖片轉 Base64 輔助
def get_base64_image(file):
    try:
        return base64.b64encode(file.getvalue()).decode()
    except: return ""

def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()
    apply_neu_theme()

    # --- 修復 404 Error: 使用標準模型的 API 設定 ---
    api_key = "AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI" # 建議檢查 Key 是否有效
    genai.configure(api_key=api_key)
    
    # 這裡使用穩定版的 gemini-1.5-flash，速度快且不易出錯
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)

    WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxgqW5gtfhyH2bgCl1G-zpmv8yTu0IzyAblqxumzT0hP0efwOl-hbL4MN6S9Du-Y3YP/exec"

    # Logo
    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png")

    tab1, tab2 = st.tabs(["💬 Project Brain Hub", "⚙️ Admin & Sync"])

    with tab1:
        col_l, col_r = st.columns([1.3, 1])
        
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean Brain Assistant")
            
            # 對話
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if p := st.chat_input("同 Firebean Brain 傾吓個 Project..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        try:
                            # 建立對話 Session 保持前後文，這會讓 AI 更容易學會「反問」
                            chat = model.start_chat(history=[
                                {"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} 
                                for m in st.session_state.messages[:-1]
                            ])
                            response = chat.send_message(p)
                            st.write(response.text)
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                        except Exception as e:
                            st.error(f"連線失敗 (404/Timeout): 請檢查 API Key 或網路環境。")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            # Logo Studio
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("Upload Logo", type=['png', 'jpg'], key="logo")
            if logo_f and st.button("🪄 一鍵轉化白色
