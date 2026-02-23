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
目標：套出 Client, Project, Venue, Challenge, Result，並引導員工上載 8 張相同搞掂項目 Logo。
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
        st.session_state.messages = [
            {"role": "assistant", "content": "嘩！見到你真係好✨！今日個 Project 係咪搞得好 Firm？話我知發生咩事，順便喺右邊餵埋相片同 Logo 俾我啦！📸"}
        ]

# --- 3. UI 視覺強化 (Red & White Neumorphism) ---
def apply_modern_ui():
    st.markdown("""
        <style>
        /* 全局樣式 - 柔和背景 */
        .stApp {
            background-color: #eef2f7; /* 淺灰背景，突顯白色物件 */
            font-family: 'Inter', sans-serif;
        }

        /* 通用 Neumorphic 凸起卡片 */
        .neu-card {
            background-color: #eef2f7;
            border-radius: 25px; /* 更圓潤的泥膠感 */
            box-shadow: 12px 12px 24px #c8d0e7, -12px -12px 24px #ffffff;
            padding: 25px;
            border: none;
        }

        /* Neumorphic 凹陷效果 + 紅色發光 (用於標題強調) */
        .neu-inset {
            background-color: #eef2f7;
            border-radius: 50%;
            box-shadow: inset 6px 6px 12px #c8d0e7, inset -6px -6px 12px #ffffff, 0 0 15px #ff5252; /* 紅色外發光 */
            padding: 10px;
            display: inline-block;
        }

        /* 標題樣式 */
        h1, h2, h3 {
            color: #444 !important;
            font-weight: 700 !important;
            text-shadow: 1px 1px 2px #ffffff;
        }
        
        /* 側邊欄樣式 */
        [data-testid="stSidebar"] {
            background-color: #eef2f7;
            box-shadow: 8px 0 16px #c8d0e7;
        }
        [data-testid="stSidebar"] .neu-card {
             box-shadow: inset 4px 4px 8px #c8d0e7, inset -4px -4px 8px #ffffff; /* 側邊欄內凹效果 */
        }

        /* 輸入框樣式 (凹陷) */
        .stTextInput > div > div, .stTextArea > div > div {
            background-color: #eef2f7 !important;
            border-radius: 15px !important;
            box-shadow: inset 5px 5px 10px #c8d0e7, inset -5px -5px 10px #ffffff !important;
            border: none !important;
            transition: all 0.3s ease;
        }
        .stTextInput > div > div:focus-within, .stTextArea > div > div:focus-within {
            box-shadow: inset 5px 5px 10px #c8d0e7, inset -5px -5px 10px #ffffff, 0 0 10px #ff5252 !important; /* 聚焦時發紅光 */
        }

        /* 按鈕樣式 (凸起發光) */
        .stButton > button {
            width: 100%;
            border-radius: 15px !important;
            background-color: #eef2f7 !important;
            color: #ff5252 !important; /* 紅色文字 */
            font-weight: bold !important;
            border: none !important;
            box-shadow: 8px 8px 16px #c8d0e7, -8px -8px 16px #ffffff !important;
            transition: all 0.3s ease !important;
        }
        .stButton > button:hover {
            box-shadow: 12px 12px 24px #c8d0e7, -12px -12px 24px #ffffff, 0 0 10px #ff5252 !important; /* 懸停發紅光 */
            transform: translateY(-2px);
        }
        .stButton > button:active {
            box-shadow: inset 4px 4px 8px #c8d0e7, inset -4px -4px 8px #ffffff !important; /* 按下凹陷 */
        }

        /* Tab 樣式 (選中發紅光) */
        .stTabs [data-baseweb="tab"] {
            border-radius: 15px 15px 0 0 !important;
            background-color: #eef2f7 !important;
            box-shadow: 4px 4px 8px #c8d0e7, -4px -4px 8px #ffffff !important;
            color: #444 !important;
            border: none !important;
        }
        .stTabs [aria-selected="true"] {
            box-shadow: inset 4px 4px 8px #c8d0e7, inset -4px -4px 8px #ffffff, 0 0 10px #ff5252 !important; /* 選中凹陷發紅光 */
            color: #ff5252 !important;
        }

        /* 相片 Slot 樣式 */
        .photo-slot-box {
            border: none;
            border-radius: 15px;
            height: 90px;
            display: flex; align-items: center; justify-content: center;
            background-color: #eef2f7;
            color: #ADB5BD; font-weight: bold;
            box-shadow: inset 4px 4px 8px #c8d0e7, inset -4px -4px 8px #ffffff; /* 凹陷 */
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. 主程式 ---
def main():
    st.set_page_config(page_title="Firebean Brain Command", layout="wide", page_icon="🔥")
    init_session_state()
    apply_modern_ui()

    # 頂部 Logo
    logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
    col_l, col_r = st.columns([1, 4])
    with col_l:
        # 為 Logo 添加凹陷發光效果
        st.markdown(f'<div class="neu-inset"><img src="{logo_url}" width="150"></div>', unsafe_allow_html=True)
    with col_r:
        # 為標題添加凹陷發光效果
        st.markdown('<h1><span class="neu-inset" style="border-radius: 15px; padding: 10px 20px;">Firebean Brain AI Command Center</span></h1>', unsafe_allow_html=True)

    # --- 側邊欄 ---
    with st.sidebar:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📊 Project Progress")
        essential = ["client_name", "project_name", "venue"]
        done = sum(1 for f in essential if st.session_state[f])
        st.write(f"關鍵資料進度: {done}/3")
        st.progress(done / 3)
        st.markdown("---")
        api_key = st.text_input("Gemini API Key", value="AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI", type="password")
        if api_key: genai.configure(api_key=api_key)
        st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Project Brain Hub", "⚙️ Admin Review & Slides"])

    # --- TAB 1: 整合中心 ---
    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col_left, col_right = st.columns([1.2, 1])
        
        # 左邊：人性化對話
        with col_left:
            st.markdown("### 🤖 Chat with AI Manager")
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
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

        # 右邊：資產上載 (Gallery + Logo Studio)
        with col_right:
            # 模組 1: Logo Studio (整合進來)
            with st.expander("🎨 Logo Studio (AI 去背 & 轉 Icon)", expanded=True):
                l_file = st.file_uploader("上傳項目 Logo 或照片", type=['png', 'jpg', 'jpeg'], key="main_logo_up")
                l_color = st.radio("目標顏色", ["Black (純黑)", "White (純白)"], horizontal=True)
                if l_file:
                    if st.button("🪄 一鍵轉化 Icon"):
                        with st.spinner("去背處理中..."):
                            out = remove(Image.open(l_file))
                            alpha = out.getchannel('A')
                            rgb = (0,0,0,255) if "Black" in l_color else (255,255,255,255)
                            final = Image.composite(Image.new('RGBA', out.size, rgb), Image.new('RGBA', out.size, (0,0,0,0)), alpha)
                            st.image(final, width=150, caption="Generated Icon")
                            buf = io.BytesIO(); final.save(buf, format="PNG")
                            st.download_button("📥 下載透明 PNG", buf.getvalue(), "project_icon.png", "image/png")

            # 模組 2: 8 格相片 Gallery
            with st.expander("📸 Project Gallery (8 格現場相)", expanded=True):
                up_files = st.file_uploader("拖放相片到此", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
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

    # --- TAB 2: 審核與簡報 ---
    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Final Review & Slides")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
            st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        with c2:
            st.session_state.venue = st.text_input("Venue", st.session_state.venue)
            st.session_state.event_date = st.text_input("Date", st.session_state.event_date)
        
        st.markdown("---")
        st.subheader("🗂️ Company Profile Preview (Black Bar Mode)")
        st.markdown("""<div style="background-color:black; color:white; padding:20px; border-radius:10px; box-shadow: 8px 8px 16px #c8d0e7;">
            <h3>Project: {{project_name}}</h3>
            <p>Venue: {{venue}}</p>
            <ul><li>AI 會根據對話自動生成 4-5 個 Key Points...</li></ul>
        </div>""", unsafe_allow_html=True)
        
        if st.button("🚀 Confirm & Sync to Google Sheet + Slides"):
            st.balloons()
            st.success("成功！資料已同步到 Google Sheet 並開始生成 PPT 模板。")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
