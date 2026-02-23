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
        st.session_state.messages = [{"role": "assistant", "content": "嘩！老細✨！個 Project 係咪搞得好 Firm？快啲話我知發生咩事，順便喺右邊餵埋相片同 Logo 俾我啦！📸"}]

# --- 3. UI 視覺強化 (淺灰泥膠版) ---
def apply_neu_theme():
    st.markdown("""
        <style>
        header {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #444; }
        h1, h2, h3 { color: #FF4B4B !important; font-weight: 800 !important; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 25px; margin-bottom: 25px; }
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, .stFileUploader {
            background-color: #F0F5FA !important; border-radius: 20px !important;
            box-shadow: inset 6px 6px 12px #d1d9e6, inset -6px -6px 12px #ffffff !important;
            border: 1px solid #F0F5FA !important;
        }
        .stButton > button { width: 100%; border-radius: 20px !important; background-color: #E0E5EC !important; color: #FF4B4B !important; font-weight: 800 !important; box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important; }
        .photo-slot-box { border-radius: 15px; height: 90px; display: flex; align-items: center; justify-content: center; background-color: #E0E5EC; box-shadow: inset 6px 6px 12px #bec3c9, inset -6px -6px 12px #ffffff; color: #aaa; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

# 輔助：圖片轉 Base64
def get_base64_image(file):
    return base64.b64encode(file.getvalue()).decode()

def main():
    st.set_page_config(page_title="Firebean Brain Command", layout="wide")
    init_session_state()
    apply_neu_theme()

    # Webhook URL (你剛剛產出的網址)
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
            if p := st.chat_input("Input details..."):
                st.session_state.messages.append({"role": "user", "content": p})
                # AI Logic Here...
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("Upload Logo", type=['png', 'jpg'], key="logo")
            # 存儲轉換後的 Logo Base64
            processed_logo_b64 = None
            if logo_f:
                if st.button("🪄 Convert to Icon"):
                    out = remove(Image.open(logo_f))
                    alpha = out.getchannel('A')
                    # 預設轉白色 (適合你的黑色邊欄)
                    final = Image.composite(Image.new('RGBA', out.size, (255,255,255,255)), Image.new('RGBA', out.size, (0,0,0,0)), alpha)
                    st.image(final, width=100)
                    buf = io.BytesIO()
                    final.save(buf, format="PNG")
                    processed_logo_b64 = base64.b64encode(buf.getvalue()).decode()
                    st.session_state['logo_b64'] = processed_logo_b64
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Max 8)")
            up_files = st.file_uploader("Upload 8 photos", type=['jpg','png'], accept_multiple_files=True)
            # 顯示 8 格 Thumbnail (略)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Final Review")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.category = st.text_input("Category (e.g. Roving Exhibition)", st.session_state.category)
        st.session_state.scope = st.text_area("Scope of Work", st.session_state.scope)
        st.session_state.challenge = st.text_area("Challenge", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution", st.session_state.solution)

        if st.button("🚀 Confirm & Sync to Master Slide"):
            with st.spinner("Uploading to Master Slide..."):
                # 準備相片 Base64 List
                img_b64_list = [get_base64_image(f) for f in up_files[:8]] if up_files else []
                
                # 構建 Payload
                payload = {
                    "project_name": st.session_state.project_name,
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
                    res = requests.post(WEBHOOK_URL, json=payload)
                    if res.status_code == 200:
                        st.balloons()
                        st.success("✅ Success! Check the last 2 pages of your Master Slide.")
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Connection Failed: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
