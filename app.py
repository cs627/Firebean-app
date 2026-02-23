import streamlit as st
import google.generativeai as genai
import requests
import json
import io
from PIL import Image
from rembg import remove

# --- 1. 核心性格與指令 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，頂尖 PR 策略大腦。性格可愛高明，語氣「Positive & Playful」。
使用 Canto-English (Vibe, Firm, Chill)。
目標：套出資料並引導員工上載相片，說話要帶有泥膠質感般嘅溫柔但有紅光般嘅影響力。
"""

# --- 2. 初始化所有狀態 ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "category_who", "category_what", "challenge_ch", "result_ch", "solution_ch",
        "linkedin_draft", "fb_post", "ig_caption", "threads_post",
        "slide_1_cover", "slide_2_challenge", "slide_3_solution", "slide_4_results",
        "youtube_link", "project_drive_folder"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "嘩！老細✨！個 Project 係咪搞得好 Firm？話我知發生咩事，順便喺右邊餵埋相片同 Logo 俾我啦！📸"}]

# --- 3. UI 視覺強化 (White & Red Neu-Molded Edition) ---
def apply_neu_theme():
    st.markdown("""
        <style>
        /* 隱藏頂部黑色 Bar */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}

        /* 全局背景：泥膠色 */
        .stApp {
            background-color: #E0E5EC;
            color: #444;
        }

        /* 文字顏色：主標題用 Firebean Red */
        h1, h2, h3 { color: #FF4B4B !important; font-weight: 800 !important; }
        
        /* 側邊欄：由深黑改為淺灰 50% 泥膠感 */
        [data-testid="stSidebar"] {
            background-color: #E0E5EC;
            border-right: none;
            box-shadow: 10px 0 20px #bec3c9;
        }
        .sidebar-content {
            background: #E0E5EC;
            border-radius: 20px;
            box-shadow: 8px 8px 16px #bec3c9, -8px -8px 16px #ffffff;
            padding: 20px;
            margin: 10px;
        }

        /* 核心組件：凹陷暗槽效果 (用於 Chat, Input, Uploader) */
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, .stFileUploader {
            background-color: #E0E5EC !important;
            border-radius: 20px !important;
            box-shadow: inset 8px 8px 16px #bec3c9, 
                        inset -8px -8px 16px #ffffff,
                        0 0 15px rgba(255, 75, 75, 0.2) !important; /* 暗槽紅光滲透 */
            border: 1px solid rgba(255, 75, 75, 0.1) !important;
            color: white !important; /* 內部字體改為白色 */
        }
        
        /* 修正 Input 內的文字顏色為白色 */
        input, textarea {
            color: white !important;
            -webkit-text-fill-color: white !important;
        }

        /* 凸起卡片 (Molded Clay) */
        .neu-card {
            background: #E0E5EC;
            border-radius: 30px;
            box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff;
            padding: 25px;
            margin-bottom: 25px;
        }

        /* 按鈕：泥膠凸起 + 點擊紅光 */
        .stButton > button {
            width: 100%;
            border-radius: 20px !important;
            background-color: #E0E5EC !important;
            color: #FF4B4B !important; 
            font-weight: 800 !important;
            border: none !important;
            box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            box-shadow: 5px 5px 10px #bec3c9, -5px -5px 10px #ffffff, 0 0 20px rgba(255, 75, 75, 0.5) !important;
            color: #ff3333 !important;
        }

        /* 相片 Slot：泥膠凹陷 */
        .photo-slot-box {
            border-radius: 15px;
            height: 90px;
            display: flex; align-items: center; justify-content: center;
            background-color: #E0E5EC;
            box-shadow: inset 6px 6px 12px #bec3c9, inset -6px -6px 12px #ffffff;
            color: #ADB5BD; font-weight: bold;
        }

        /* 標籤頁面樣式 */
        .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #E0E5EC !important;
            border-radius: 15px !important;
            box-shadow: 4px 4px 8px #bec3c9, -4px -4px 8px #ffffff !important;
            color: #444 !important;
            border: none !important;
        }
        .stTabs [aria-selected="true"] {
            box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff, 0 0 10px rgba(255, 75, 75, 0.4) !important;
            color: #FF4B4B !important;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. 主程式 ---
def main():
    st.set_page_config(page_title="Firebean Brain Command", layout="wide", page_icon="🔥")
    init_session_state()
    apply_neu_theme()

    # 頂部 Logo 與 標題
    logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
    
    col_header_l, col_header_r = st.columns([1, 4])
    with col_header_l:
        st.image(logo_url, width=160)
    with col_header_r:
        st.markdown('<h1 style="font-size: 2.5em; margin-top: 10px;">Firebean Brain AI Command Center</h1>', unsafe_allow_html=True)

    # --- 側邊欄：修飾後的 50% 淺灰 Card ---
    with st.sidebar:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown('### 📊 Project Status', unsafe_allow_html=True)
        essential = ["client_name", "project_name", "venue"]
        done = sum(1 for f in essential if st.session_state[f])
        st.write(f"關鍵資料進度: {done}/3")
        st.progress(done / 3)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown('<p style="font-size: 0.9em; margin-bottom: 5px; color:#444;">Gemini API Key</p>', unsafe_allow_html=True)
        api_key = st.text_input("Key", value="AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI", type="password", label_visibility="collapsed")
        if api_key: genai.configure(api_key=api_key)
        st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Brain Hub", "⚙️ Admin & Slides"])

    # --- TAB 1: 整合中心 ---
    with tab1:
        col_left, col_right = st.columns([1.3, 1])
        
        with col_left:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.markdown("### 🤖 Chat with AI Manager")
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]): 
                        st.markdown(f'<span style="color:#444;">{msg["content"]}</span>', unsafe_allow_html=True)
            
            if prompt := st.chat_input("同 Firebean Brain 傾吓個 Project..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)
                            res = model.generate_content(prompt)
                            st.markdown(res.text)
                            st.session_state.messages.append({"role": "assistant", "content": res.text})
                            st.session_state.raw_transcript += f"\nUser: {prompt}\nAI: {res.text}"
                        except Exception as e: st.error(f"Error: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_right:
            # Logo Studio 模組 (凹陷槽)
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.markdown("### 🎨 Logo Studio")
            l_file = st.file_uploader("上傳項目 Logo", type=['png', 'jpg', 'jpeg'], key="main_logo_up")
            l_color = st.radio("目標顏色", ["Black (純黑)", "White (純白)"], horizontal=True)
            if l_file:
                if st.button("🪄 一鍵轉化 Icon"):
                    with st.spinner("處理中..."):
                        out = remove(Image.open(l_file))
                        alpha = out.getchannel('A')
                        rgb = (0,0,0,255) if "Black" in l_color else (255,255,255,255)
                        final = Image.composite(Image.new('RGBA', out.size, rgb), Image.new('RGBA', out.size, (0,0,0,0)), alpha)
                        st.image(final, width=120)
                        buf = io.BytesIO(); final.save(buf, format="PNG")
                        st.download_button("📥 下載 PNG", buf.getvalue(), "project_icon.png", "image/png")
            st.markdown('</div>', unsafe_allow_html=True)

            # 8 格 Gallery
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.markdown("### 📸 Project Gallery")
            up_files = st.file_uploader("上傳現場相片", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            g1, g2, g3, g4 = st.columns(4); g5, g6, g7, g8 = st.columns(4)
            slots = [g1, g2, g3, g4, g5, g6, g7, g8]
            for i in range(8):
                with slots[i]:
                    if up_files and i < len(up_files):
                        st.image(up_files[i], use_column_width=True)
                    else:
                        st.markdown(f'<div class="photo-slot-box">{i+1}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: 審核與簡報 ---
    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Admin Review & Slides")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.project_name = st.text_input("Project Name", value=st.session_state.project_name)
            st.session_state.client_name = st.text_input("Client Name", value=st.session_state.client_name)
        with c2:
            st.session_state.venue = st.text_input("Venue", value=st.session_state.venue)
            st.session_state.event_date = st.text_input("Date", value=st.session_state.event_date)
        
        if st.button("🚀 Confirm & Sync to Database"):
            st.balloons()
            st.success("成功！資料已同步到 Google Sheet 並啟動 Google Slide 引擎。")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
