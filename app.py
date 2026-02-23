import streamlit as st
import google.generativeai as genai
import requests
import json
import io
from PIL import Image
from rembg import remove

# --- 1. 系統核心指令 ---
FIREBEAN_BRAIN_GUIDELINES = """
You are "Firebean Brain", the core AI of Firebean PR agency.
Tone: "Institutional Cool".
Tasks:
1. Generate PR content (EN, CH, JP) and Social Media posts.
2. Generate a 4-page Company Profile Slide Script (Cover, Challenge, Solution, Results).
Return output ONLY as a valid JSON object.
"""

# --- 2. 初始化所有欄位 (解決 AttributeError) ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "category_who", "category_what", "highlight_order", "youtube_link", 
        "gallery_image_urls", "project_drive_folder", "best_image_url", 
        "client_logo_url", "youtube_embed_code",
        "title_en", "challenge_en", "solution_en", "result_en",
        "title_ch", "challenge_ch", "solution_ch", "result_ch",
        "title_jp", "challenge_jp", "solution_jp", "result_jp",
        "slide_points_en", "linkedin_draft", "fb_post", "ig_caption", 
        "threads_post", "newsletter_topic",
        "slide_1_cover", "slide_2_challenge", "slide_3_solution", "slide_4_results"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello Dickson! Firebean Brain is fully fixed and online. How can I help with your project today?"}
        ]

# --- 3. UI 樣式 ---
def apply_custom_style():
    st.markdown("""
        <style>
        .stApp { background-color: #e0e5ec; }
        .neu-card { background-color: #e0e5ec; border-radius: 15px; box-shadow: 8px 8px 16px #b8bec5, -8px -8px 16px #ffffff; padding: 20px; margin-bottom: 20px; }
        .slide-preview { background-color: white; border: 2px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 10px; color: #333; }
        .stButton>button { border-radius: 12px; box-shadow: 5px 5px 10px #b8bec5, -5px -5px 10px #ffffff; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. 主程式 ---
def main():
    # 必須先設定 Page Config
    st.set_page_config(page_title="Firebean AI Command Center", layout="wide", page_icon="🔥")
    
    # 必須先初始化 State，再執行後面的代碼 (解決 AttributeError)
    init_session_state()
    apply_custom_style()

    # 頂部 Logo
    logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
    st.image(logo_url, width=280)

    # --- 側邊欄設定 ---
    with st.sidebar:
        st.header("🔐 Config")
        # 預設 API Key
        default_key = "AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI"
        api_key = st.text_input("Gemini API Key", value=default_key, type="password")
        
        if api_key:
            genai.configure(api_key=api_key)
            st.success("API Connected")
        
        st.markdown("---")
        st.subheader("📊 Sync Assets")
        # 修正賦值方式
        st.session_state.youtube_link = st.text_input("YouTube URL", value=st.session_state.youtube_link)
        st.session_state.project_drive_folder = st.text_input("Google Drive Link", value=st.session_state.project_drive_folder)

    # --- 功能標籤 ---
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat & Input", "🎨 Logo Studio", "⚙️ Admin Review", "🗂️ Slide Script"])

    # TAB 1: 對話
    with tab1:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        if prompt := st.chat_input("Tell me about the project..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.raw_transcript += f"\n\n[Update]: {prompt}"
            with st.chat_message("user"): st.markdown(prompt)

        if st.button("🚀 Activate Firebean Brain", type="primary"):
            with st.spinner("Processing..."):
                try:
                    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=FIREBEAN_BRAIN_GUIDELINES)
                    response = model.generate_content(st.session_state.raw_transcript, generation_config={"response_mime_type": "application/json"})
                    res_data = json.loads(response.text)
                    for k, v in res_data.items():
                        if k in st.session_state: st.session_state[k] = v
                    st.success("Assets Generated!")
                except Exception as e: st.error(f"Error: {str(e)}")

    # TAB 2: Logo Studio
    with tab2:
        st.header("🎨 AI Logo Studio")
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            logo_f = st.file_uploader("Upload logo photo", type=['png', 'jpg', 'jpeg'])
        with col_c2:
            l_color = st.radio("Icon Color", ["Black (純黑)", "White (純白)"])

        if logo_f:
            input_img = Image.open(logo_f)
            if st.button("🪄 Convert to Icon"):
                with st.spinner("Removing background..."):
                    out_img = remove(input_img)
                    alpha = out_img.getchannel('A')
                    rgb = (0,0,0,255) if "Black" in l_color else (255,255,255,255)
                    final_i = Image.composite(Image.new('RGBA', out_img.size, rgb), Image.new('RGBA', out_img.size, (0,0,0,0)), alpha)
                    st.image(final_i, width=200)
                    buf = io.BytesIO()
                    final_i.save(buf, format="PNG")
                    st.download_button("📥 Download PNG", buf.getvalue(), f"icon_{l_color}.png", "image/png")

    # TAB 3: Admin Review
    with tab2: # 這裡是修正原本標籤顯示的問題
        st.header("⚙️ Admin Review")
        st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        if st.button("✅ Save to Google Sheet"):
            st.info("Webhook Sync logic goes here.")

    # TAB 4: Slide Script
    with tab4:
        st.header("🗂️ Company Profile Slide Script")
        s_cols = st.columns(2)
        slides = [("Slide 1", "slide_1_cover"), ("Slide 2", "slide_2_challenge"), ("Slide 3", "slide_3_solution"), ("Slide 4", "slide_4_results")]
        for i, (title, key) in enumerate(slides):
            with s_cols[i % 2]:
                st.markdown(f'<div class="slide-preview"><b>{title}</b><br>{st.session_state[key]}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
