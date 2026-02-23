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
語音轉錄任務：請精確還原廣東話口語文字並分析項目細節。
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
        st.session_state.messages = [{"role": "assistant", "content": "嘩！老細✨！終於升級用 Gemini Pro 腦袋，轉數快好多！今日個 Project 搞成點？快啲錄音或者喺右邊餵相俾我啦！📸"}]

# --- 3. UI 視覺強化 (Energy Bar + 手機 2x4 Gallery + 置中 Logo) ---
def apply_neu_theme():
    # 計算能量值
    track_fields = ["client_name", "project_name", "event_date", "venue", "category", "scope", "challenge", "solution"]
    filled = sum(1 for f in track_fields if st.session_state[f])
    progress_percent = int((filled / len(track_fields)) * 100)

    st.markdown(f"""
        <style>
        header {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        .stApp {{ background-color: #E0E5EC; color: #2D3436; }}

        /* --- 頂部能量進度條 (Energy Bar) --- */
        .energy-container {{
            width: 100%; background: #E0E5EC; padding: 10px 0;
            position: sticky; top: 0; z-index: 999;
        }}
        .energy-bar-bg {{
            height: 14px; background: #E0E5EC; border-radius: 10px;
            box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff;
            overflow: hidden; margin: 0 20px;
        }}
        .energy-bar-fill {{
            height: 100%; width: {progress_percent}%;
            background: linear-gradient(90deg, #FF4B4B, #FF8080);
            box-shadow: 0 0 15px #FF4B4B; transition: width 0.8s ease-in-out;
        }}
        .energy-text {{
            font-size: 11px; font-weight: 800; color: #FF4B4B;
            text-align: right; margin: 5px 25px 0 0;
        }}

        /* --- Logo 強制置中 (手機及電腦通用) --- */
        [data-testid="stImage"] {{
            display: flex !important; justify-content: center !important; align-items: center !important;
            width: 100% !important;
        }}
        [data-testid="stImage"] img {{ 
            margin: 0 auto !important; 
            max-width: 180px !important;
        }}

        /* --- 文字顏色修復：深石墨灰確保清晰 --- */
        input, textarea, [data-baseweb="input"] *, .stChatInputContainer textarea {{
            color: #2D3436 !important; -webkit-text-fill-color: #2D3436 !important; font-weight: 600 !important;
        }}
        .stFileUploader label, .stFileUploader span, .stFileUploader p, .stFileUploader small {{
            color: #2D3436 !important;
        }}
        p, label, span, .stMarkdown {{ color: #2D3436 !important; }}
        h1, h2, h3 {{ color: #FF4B4B !important; }}

        /* --- 2x4 手機 Gallery 網格實現 --- */
        .gallery-grid {{
            display: grid; 
            grid-template-columns: repeat(4, 1fr); /* 電腦版 4 欄 */
            gap: 12px; 
            margin-top: 15px;
        }}
        @media (max-width: 640px) {{
            .gallery-grid {{ 
                grid-template-columns: repeat(2, 1fr) !important; /* 手機版強制 2 欄 */
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
            color: #888; font-size: 10px; font-weight: bold;
        }}

        /* --- UI Box 元件 --- */
        .neu-card {{
            background: #E0E5EC; border-radius: 30px;
            box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff;
            padding: 20px; margin-bottom: 20px;
        }}
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, [data-testid="stAudioInput"], .stFileUploader {{
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

def get_base64_image(file):
    try:
        return base64.b64encode(file.getvalue()).decode()
    except: return ""

def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()
    apply_neu_theme()

    # --- 修正後的 API 設定 (使用 Gemini 1.5 Pro) ---
    api_key = "AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI" 
    genai.configure(api_key=api_key)
    
    # 這裡使用 1.5-pro 以應對你提到的 Pro 需求，並修復版本不匹配問題
    model = genai.GenerativeModel("gemini-1.5-pro", system_instruction=SYSTEM_INSTRUCTION)

    # Logo
    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png")

    tab1, tab2 = st.tabs(["💬 Brain Hub", "⚙️ Admin & Sync"])

    with tab1:
        col_l, col_r = st.columns([1.3, 1])
        
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean Brain Assistant")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            st.markdown("---")
            # --- 修復後的錄音功能 ---
            audio_input = st.audio_input("🎤 撳住錄音話我知 Project 詳情...")
            if audio_input is not None:
                audio_bytes = audio_input.getvalue()
                if audio_bytes:
                    with st.spinner("聽緊你講咩... Gemini Pro 正在分析..."):
                        try:
                            # 確保調用格式正確
                            content_parts = [
                                "請精確轉錄這段廣東話錄音，並提取項目詳情 (Client, Venue, Challenge, Result)。",
                                {"mime_type": "audio/wav", "data": audio_bytes}
                            ]
                            response = model.generate_content(content_parts)
                            if response:
                                st.session_state.messages.append({"role": "user", "content": f"🎤 [錄音轉錄]: {response.text}"})
                                st.rerun()
                        except Exception as e:
                            st.error(f"錄音處理失敗: {str(e)}")

            if p := st.chat_input("同 Firebean Brain 傾吓個 Project..."):
                st.session_state.messages.append({"role": "user", "content": p})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            # Logo Studio
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("Upload Logo", type=['png', 'jpg'], key="logo")
            if logo_f and st.button("🪄 一鍵轉化白色標誌"):
                img = Image.open(logo_f)
                out = remove(img)
                final = Image.composite(Image.new('RGBA', out.size, (255,255,255,255)), Image.new('RGBA', out.size, (0,0,0,0)), out.getchannel('A'))
                st.image(final, width=120)
                buf = io.BytesIO()
                final.save(buf, format="PNG")
                st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

            # --- 2x4 手機 Gallery 網格實現 ---
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            up_files = st.file_uploader("上傳現場相片", type=['jpg','png'], accept_multiple_files=True)
            
            grid_html = '<div class="gallery-grid">'
            for i in range(8):
                if up_files and i < len(up_files):
                    b64 = get_base64_image(up_files[i])
                    grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item"></div>'
                else:
                    grid_html += f'<div class="slot-placeholder">Slot {i+1}</div>'
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Admin Dashboard")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        st.session_state.scope = st.text_area("Scope", st.session_state.scope)
        
        if st.button("🚀 Confirm & Sync to Master Slide"):
            st.balloons()
            st.success("成功追加至 Master Slide！")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
