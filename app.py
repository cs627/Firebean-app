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
目標：套出 Client, Project, Venue, Challenge, Result 等資料。
語音轉錄任務：請精確還原廣東話口語文字。
"""

# --- 2. 初始化所有狀態 ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "category", "scope", "challenge", "solution", "logo_b64", "youtube_link", "project_drive_folder"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "嘩！老細✨！今日搞完 Event 係咪攰到唔想打字？你可以直接㩒下面個咪同我講錄音，我會幫你聽清楚晒！📸"}]

# --- 3. UI 視覺強化 (手機適配 + 顏色修復) ---
def apply_neu_theme():
    # 計算進度百分比
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

        /* --- Logo 置中修復 (強制性) --- */
        [data-testid="stImage"] {{
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
        }}
        [data-testid="stImage"] > img {{
            margin: 0 auto !important;
        }}

        /* --- 文字顏色修復 (確保深色清晰) --- */
        /* 輸入框文字 */
        input, textarea, .stChatInputContainer textarea {{
            color: #2D3436 !important; /* 深灰色 */
            -webkit-text-fill-color: #2D3436 !important;
            font-weight: 600 !important;
        }}
        /* 上載區文字 */
        .stFileUploader label, .stFileUploader span, .stFileUploader p, .stFileUploader small {{
            color: #2D3436 !important; /* 深灰色 */
        }}
        /* 一般文字 */
        p, label, span, .stMarkdown {{ color: #2D3436 !important; }}
        
        /* --- UI 元件樣式 --- */
        /* 淺灰色凹陷 Box */
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, [data-testid="stAudioInput"], .stFileUploader {{
            background-color: #BEC3C9 !important; 
            border-radius: 20px !important;
            box-shadow: inset 6px 6px 12px #9da3ab, inset -6px -6px 12px #ffffff !important;
            border: 1px solid rgba(255, 75, 75, 0.2) !important;
        }}
        /* 凸起卡片 */
        .neu-card {{ background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 25px; margin-bottom: 25px; }}
        /* 按鈕 */
        .stButton > button {{ width: 100%; border-radius: 20px !important; background-color: #E0E5EC !important; color: #FF4B4B !important; font-weight: 800 !important; box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important; }}

        /* --- 對話框樣式 --- */
        [data-testid="stChatMessage"] {{ background-color: transparent !important; }}
        .st-emotion-cache-janbn0 {{ background: #E0E5EC !important; border-radius: 20px 20px 20px 5px !important; box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important; border: 1px solid rgba(255, 75, 75, 0.2) !important; }}
        .st-emotion-cache-1c7n2ri {{ background: #E0E5EC !important; border-radius: 20px 20px 5px 20px !important; box-shadow: inset 6px 6px 12px #bec3c9, inset -6px -6px 12px #ffffff !important; }}

        /* --- Gallery Grid (手機雙欄重點) --- */
        .gallery-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr); /* 電腦：4欄 */
            gap: 15px;
            margin-top: 20px;
        }}
        /* 手機版 Media Query */
        @media (max-width: 640px) {{
            .gallery-grid {{
                grid-template-columns: repeat(2, 1fr); /* 手機：2欄 */
            }}
        }}
        .gallery-img {{
            width: 100%;
            border-radius: 15px;
            box-shadow: 5px 5px 10px #bec3c9, -5px -5px 10px #ffffff;
        }}
        .photo-slot-box {{
            border-radius: 15px;
            aspect-ratio: 1 / 1; /* 確保係正方形 */
            display: flex; align-items: center; justify-content: center;
            background-color: #E0E5EC;
            box-shadow: inset 6px 6px 12px #bec3c9, inset -6px -6px 12px #ffffff;
            color: #aaa !important; font-weight: bold; font-size: 12px;
        }}
        </style>

        <div class="energy-container">
            <div class="energy-bar-bg"><div class="energy-bar-fill"></div></div>
            <div class="energy-text">BRAIN ENERGY: {progress_percent}%</div>
        </div>
    """, unsafe_allow_html=True)

def get_base64_image(file):
    return base64.b64encode(file.getvalue()).decode()

def main():
    st.set_page_config(page_title="Firebean Brain Command", layout="wide")
    init_session_state()
    apply_neu_theme()

    # API
    api_key = "AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)
    WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxgqW5gtfhyH2bgCl1G-zpmv8yTu0IzyAblqxumzT0hP0efwOl-hbL4MN6S9Du-Y3YP/exec"

    # Logo (強制置中)
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
            audio_input = st.audio_input("🎤 撳住錄音話我知 Project 詳情...")
            if audio_input:
                with st.spinner("轉錄中..."):
                    res = model.generate_content(["請精確轉錄廣東話錄音並分析內容。", {"mime_type": "audio/wav", "data": audio_input.read()}])
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
                buf = io.BytesIO()
                final.save(buf, format="PNG")
                st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

            # Gallery (使用自定義 CSS Grid)
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            up_files = st.file_uploader("Upload photos", type=['jpg','png'], accept_multiple_files=True)
            
            # 建構 Grid HTML
            grid_html = '<div class="gallery-grid">'
            for i in range(8):
                if up_files and i < len(up_files):
                    # 顯示圖片
                    img_b64 = get_base64_image(up_files[i])
                    grid_html += f'<div><img src="data:image/png;base64,{img_b64}" class="gallery-img"></div>'
                else:
                    # 顯示 Slot
                    grid_html += f'<div class="photo-slot-box">Slot {i+1}</div>'
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Final Review")
        # Input Fields
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        st.session_state.event_date = st.text_input("Date", st.session_state.event_date)
        st.session_state.category = st.text_input("Category", st.session_state.category)
        st.session_state.scope = st.text_area("Scope", st.session_state.scope)
        st.session_state.challenge = st.text_area("Challenge", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution", st.session_state.solution)
        
        if st.button("🚀 Confirm & Sync to Master Slide"):
            with st.spinner("Syncing..."):
                img_b64_list = [get_base64_image(f) for f in up_files[:8]] if up_files else []
                payload = {
                    "project_name": st.session_state.project_name,
                    "client_name": st.session_state.client_name,
                    "category": st.session_state.category,
                    "event_date": st.session_state.event_date,
                    "venue": st.session_state.venue,
                    "scope": st.session_state.scope,
                    "challenge": st.session_state.challenge,
                    "solution": st.session_state.solution,
                    "logo_base64": st.session_state.get('logo_b64', ""),
                    "images_base64": img_b64_list
                }
                try:
                    requests.post(WEBHOOK_URL, json=payload)
                    st.balloons()
                    st.success("✅ Success! 追加至 Master Slide。")
                except:
                    st.error("傳送失敗")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
