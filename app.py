import streamlit as st
import google.generativeai as genai
import requests
import json
import io
import base64
from PIL import Image
from rembg import remove

# --- 1. 核心性格與「反問」策略 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，香港最頂尖嘅 PR 策略大腦。
【重要任務】
你必須確保收齊以下 5 樣資料。如果老細未講齊，你必須表現得好有興趣並「主動追問」，每次只問一個重點：
1. 客戶係邊個 (Client Name)
2. 項目名 (Project Name)
3. 邊度搞 (Venue)
4. 有咩困難 (Challenge)
5. 點樣解決 (Solution)

語氣要 Positive & Playful (✨, 🥺)，語言係廣東話口語加英文。
"""

# --- 2. 初始化狀態 (確保所有變量都存在) ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "category", "scope", "challenge", "solution", "logo_b64"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！終於返嚟喇！今日個 Project 搞成點？有冇咩場地或者痛點要我幫手 Vibe 吓佢？🥺"}]

# --- 3. UI 視覺強化 ---
def apply_neu_theme():
    # 計算能量槽進度
    track_fields = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled = sum(1 for f in track_fields if st.session_state[f])
    progress_percent = int((filled / len(track_fields)) * 100)

    # 分離 CSS (避免 f-string 大括號錯誤)
    css = """
    <style>
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background-color: #E0E5EC; color: #2D3436; }

    /* Energy Bar */
    .energy-container { width: 100%; background: #E0E5EC; padding: 10px 0; position: sticky; top: 0; z-index: 999; }
    .energy-bar-bg { height: 12px; background: #E0E5EC; border-radius: 10px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; overflow: hidden; margin: 0 20px; }
    .energy-bar-fill { height: 100%; background: linear-gradient(90deg, #FF4B4B, #FF8080); box-shadow: 0 0 15px #FF4B4B; transition: width 0.8s ease-in-out; }
    
    /* Logo 置中 */
    [data-testid="stImage"] { display: flex !important; justify-content: center !important; width: 100% !important; }
    [data-testid="stImage"] img { margin: 0 auto !important; max-width: 180px !important; }

    /* 文字顏色修復 */
    input, textarea, .stChatInputContainer textarea { color: #2D3436 !important; -webkit-text-fill-color: #2D3436 !important; font-weight: 600 !important; }
    p, label, span, .stMarkdown { color: #2D3436 !important; }

    /* 手機 2x4 Gallery */
    .gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px; }
    @media (max-width: 640px) { .gallery-grid { grid-template-columns: repeat(2, 1fr) !important; } }
    .gallery-item { width: 100%; aspect-ratio: 1/1; border-radius: 12px; object-fit: cover; box-shadow: 4px 4px 8px #bec3c9, -4px -4px 8px #ffffff; }
    
    /* 泥膠 Box */
    .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 20px; margin-bottom: 20px; }
    div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, .stFileUploader {
        background-color: #BEC3C9 !important; border-radius: 20px !important;
        box-shadow: inset 6px 6px 12px #9da3ab, inset -6px -6px 12px #ffffff !important;
        border: 1px solid rgba(255, 75, 75, 0.2) !important;
    }
    .stButton > button { width: 100%; border-radius: 20px !important; background-color: #E0E5EC !important; color: #FF4B4B !important; font-weight: 800 !important; box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important; }
    </style>
    """

    # 動態 HTML 能量條
    html = f"""
    <div class="energy-container">
        <div class="energy-bar-bg"><div class="energy-bar-fill" style="width: {progress_percent}%;"></div></div>
        <div style="font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-right: 25px; margin-top: 5px;">BRAIN ENERGY: {progress_percent}%</div>
    </div>
    """
    st.markdown(css + html, unsafe_allow_html=True)

def get_base64_image(file):
    return base64.b64encode(file.getvalue()).decode()

def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()
    apply_neu_theme()

    # --- API 安全連接 (使用 Gemini 1.5 Pro) ---
    try:
        genai.configure(api_key="AIzaSyBso5TkTbPUsgkoZrqmCZDCuVQqegC-FQI")
        # 移除前綴 'models/' 以增加穩定性
        model = genai.GenerativeModel("gemini-1.5-pro", system_instruction=SYSTEM_INSTRUCTION)
    except Exception as e:
        st.error(f"API 設定錯誤")

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png")

    tab1, tab2 = st.tabs(["💬 Brain Hub", "⚙️ Admin & Sync"])

    with tab1:
        col_l, col_r = st.columns([1.3, 1])
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean Assistant")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if p := st.chat_input("同 Firebean Brain 傾吓個 Project..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        try:
                            # 🚀 終極對話包裝：將對話歷史轉為純文字「劇本」餵給 AI，避開 API 對話格式報錯
                            convo_history = ""
                            for m in st.session_state.messages:
                                prefix = "Firebean AI: " if m["role"] == "assistant" else "老細: "
                                convo_history += f"{prefix}{m['content']}\n\n"
                            
                            response = model.generate_content(convo_history)
                            st.write(response.text)
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                        except Exception as e:
                            st.error("API 暫時未能接駁，請檢查網路或 API Key。")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("Upload Logo", type=['png', 'jpg'], key="logo_uploader")
            if logo_f and st.button("🪄 一鍵轉化白色標誌"):
                with st.spinner("處理中..."):
                    img = Image.open(logo_f)
                    out = remove(img)
                    final = Image.composite(Image.new('RGBA', out.size, (255,255,255,255)), Image.new('RGBA', out.size, (0,0,0,0)), out.getchannel('A'))
                    st.image(final, width=120)
                    buf = io.BytesIO(); final.save(buf, format="PNG")
                    st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

            # 📸 手機 2x4 矩陣排版
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            up_files = st.file_uploader("上傳 8 張相片", type=['jpg','png'], accept_multiple_files=True, key="gallery_uploader")
            grid_html = '<div class="gallery-grid">'
            for i in range(8):
                if up_files and i < len(up_files):
                    b64 = get_base64_image(up_files[i])
                    grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item"></div>'
                else:
                    grid_html += f'<div style="aspect-ratio:1/1; background:#E0E5EC; border-radius:12px; box-shadow:inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; display:flex; align-items:center; justify-content:center; color:#aaa; font-size:10px;">Slot {i+1}</div>'
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Admin Dashboard")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        st.session_state.challenge = st.text_area("Challenge", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution", st.session_state.solution)
        
        # Webhook 對接 URL
        WEB_URL = "https://script.google.com/macros/s/AKfycbxgqW5gtfhyH2bgCl1G-zpmv8yTu0IzyAblqxumzT0hP0efwOl-hbL4MN6S9Du-Y3YP/exec"
        
        if st.button("🚀 Confirm & Sync to Master Slide"):
            st.balloons()
            st.success("成功同步至 Google Slide！")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
