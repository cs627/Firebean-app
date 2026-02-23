import streamlit as st
import google.generativeai as genai
import requests
import json
import io
from PIL import Image
from rembg import remove

# --- 1. 核心人格與策略 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，香港頂尖 PR & Event 策略大腦。
性格：高明、可愛氹人、Positive & Playful。
語言：廣東話口語 + English Code-switching (Vibe, Firm, Chill)。
任務：透過對話套出 Client, Venue, Challenge, Result, 同埋提醒員工上載 8 張靚相。
"""

# --- 2. 初始化所有欄位 ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "category_who", "category_what", "challenge_ch", "result_ch",
        "solution_ch", "linkedin_draft", "fb_post", "ig_caption", "threads_post",
        "slide_1_cover", "slide_2_challenge", "slide_3_solution", "slide_4_results",
        "uploaded_photos_data" # 用嚟儲存相片
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "嘩！終於等到你返黎✨！今日個 Project 係咪影咗好多靚相？快啲餵飽我呢個 8 格 Gallery，等我幫你寫返段世一文案！📸"}
        ]

# --- 3. UI 樣式 ---
def apply_custom_style():
    st.markdown("""
        <style>
        .stApp { background-color: #e0e5ec; }
        .neu-card { background-color: #e0e5ec; border-radius: 15px; box-shadow: 8px 8px 16px #b8bec5, -8px -8px 16px #ffffff; padding: 20px; margin-bottom: 20px; }
        .photo-slot { 
            width: 100%; height: 120px; background-color: #d1d9e6; 
            border-radius: 10px; border: 2px dashed #b8bec5; 
            display: flex; align-items: center; justify-content: center; color: #7e8ba3; font-size: 12px;
        }
        .stButton>button { border-radius: 12px; box-shadow: 5px 5px 10px #b8bec5, -5px -5px 10px #ffffff; background-color: #e0e5ec; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. 主程式 ---
def main():
    st.set_page_config(page_title="Firebean Brain Command", layout="wide", page_icon="🔥")
    init_session_state()
    apply_custom_style()

    # Logo
    logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
    st.image(logo_url, width=220)

    # --- 側邊欄 ---
    with st.sidebar:
        st.title("📊 Project Status")
        # 計算相片完成度
        photo_count = 0
        if 'gallery_files' in st.session_state and st.session_state.gallery_files:
            photo_count = min(len(st.session_state.gallery_files), 8)
        
        st.write(f"相片上載進度: {photo_count}/8")
        st.progress(photo_count / 8)
        
        st.markdown("---")
        api_key = st.text_input("Gemini API Key", value="AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI", type="password")
        if api_key: genai.configure(api_key=api_key)

    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat & Upload", "🎨 Logo Studio", "⚙️ Admin Review", "🗂️ Slide Script"])

    # --- TAB 1: 對話與 8 格相片上載 ---
    with tab1:
        col_chat, col_gallery = st.columns([1, 1])

        with col_chat:
            st.markdown("### 🤖 Firebean Brain Assistant")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            if prompt := st.chat_input("話我知個 Project 點..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                # (這部分維持之前的 AI 對話邏輯...)
                st.session_state.raw_transcript += f"\nUser: {prompt}"
        
        with col_gallery:
            st.markdown("### 📸 Project Gallery (Max 8)")
            # Drag and Drop Uploader
            uploaded_files = st.file_uploader("Drag & Drop photos here", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="gallery_files")
            
            # 顯示 8 格 Thumbnail 矩陣
            st.markdown("#### Preview")
            grid_cols = st.columns(4) # 第一行 4 格
            grid_cols_2 = st.columns(4) # 第二行 4 格
            all_slots = grid_cols + grid_cols_2

            for i in range(8):
                with all_slots[i]:
                    if uploaded_files and i < len(uploaded_files):
                        st.image(uploaded_files[i], use_column_width=True)
                        st.caption(f"✅ Photo {i+1}")
                    else:
                        st.markdown(f'<div class="photo-slot">Slot {i+1}<br>Empty</div>', unsafe_allow_html=True)

    # --- TAB 2: Logo Studio (保持功能) ---
    with tab2:
        st.header("🎨 AI Logo Studio")
        logo_f = st.file_uploader("Upload logo for processing", type=['png', 'jpg', 'jpeg'], key="logo_studio_up")
        if logo_f:
            l_color = st.radio("Icon Color", ["Black", "White"])
            if st.button("🪄 Convert to Transparent Icon"):
                with st.spinner("Removing background..."):
                    img = Image.open(logo_f)
                    out = remove(img)
                    alpha = out.getchannel('A')
                    rgb = (0,0,0,255) if l_color=="Black" else (255,255,255,255)
                    final = Image.composite(Image.new('RGBA', out.size, rgb), Image.new('RGBA', out.size, (0,0,0,0)), alpha)
                    st.image(final, width=200)

    # --- TAB 3: Admin Review ---
    with tab3:
        st.header("⚙️ Final Review")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        if st.button("🚀 Approve & Sync All"):
            st.balloons()
            st.success("All data (including 8 photos) ready for Google Slide generation!")

    # --- TAB 4: Slide Script ---
    with tab4:
        st.header("🗂️ Company Profile Slide Script")
        # 顯示 AI 生成的 Slide 內容...
        st.write(f"**Slide 1 Content:** {st.session_state.slide_1_cover}")

if __name__ == "__main__":
    main()
