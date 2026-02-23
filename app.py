import streamlit as st
import google.generativeai as genai
import requests
import json
from PIL import Image

# --- 1. 系統核心設定 (SYSTEM PROMPT) ---
FIREBEAN_BRAIN_GUIDELINES = """
You are "Firebean Brain", the core AI of Firebean, a top HK PR agency.
Identity: "The Architect of Public Engagement".
Tone: "Institutional Cool" (Authority + Lifestyle Creativity).

TASK:
1. Analyze project details and generate PR content (EN, CH, JP).
2. Generate Social Media drafts (LinkedIn, FB, IG, Threads).
3. Generate a 4-page Company Profile Slide Script:
   - Slide 1: Cover (Project title/context)
   - Slide 2: Challenge (3 pain points)
   - Slide 3: Solution (Creative strategy)
   - Slide 4: Results (Data & Impact)

Return the output ONLY as a valid JSON object.
"""

# --- 2. 初始化所有欄位 (SESSION STATE) ---
def init_session_state():
    # 35 個核心欄位 + 簡報欄位
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
            {"role": "assistant", "content": "Hello Dickson! I am Firebean Brain. Ready to turn policy into play? Tell me about your latest project!"}
        ]

# --- 3. UI 樣式設定 (NEUMORPHISM) ---
def apply_custom_style():
    st.markdown("""
        <style>
        .stApp { background-color: #e0e5ec; }
        .neu-card {
            background-color: #e0e5ec;
            border-radius: 15px;
            box-shadow: 8px 8px 16px #b8bec5, -8px -8px 16px #ffffff;
            padding: 20px;
            margin-bottom: 20px;
            color: #4a4a4a;
        }
        .slide-preview {
            background-color: white;
            border: 2px solid #ddd;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            min-height: 150px;
        }
        .stButton>button {
            border-radius: 12px;
            box-shadow: 5px 5px 10px #b8bec5, -5px -5px 10px #ffffff;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. 主程式 ---
def main():
    st.set_page_config(page_title="Firebean AI Command Center", layout="wide", page_icon="🔥")
    apply_custom_style()
    init_session_state()

    # 頂部 Logo (使用 GitHub Raw 連結)
    logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
    st.image(logo_url, width=280)
    st.title("🔥 Firebean AI Command Center")

    # --- 側邊欄：設定與進度 ---
    with st.sidebar:
        st.header("🔐 Config")
        api_key = st.text_input("Gemini API Key", type="password")
        if api_key:
            genai.configure(api_key=api_key)
            st.success("API Connected")
        
        st.markdown("---")
        st.subheader("📊 Sync Assets")
        st.session_state.project_drive_folder = st.text_input("Google Drive Link", st.session_state.project_drive_folder)
        st.session_state.youtube_link = st.text_input("YouTube URL", st.session_state.youtube_link)

    # --- 功能標籤頁 ---
    tab1, tab2, tab3 = st.tabs(["💬 Chat & Input", "⚙️ Admin Review", "🗂️ Slide Script"])

    # TAB 1: 對話與資料擷取
    with tab1:
        st.markdown('<div class="neu-card"><h3>🤖 Firebean Brain Assistant</h3></div>', unsafe_allow_html=True)
        
        # 顯示對話紀錄
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 對話輸入
        if prompt := st.chat_input("Input event details (e.g., Client, Venue, Results)..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.raw_transcript += f"\n\n[Update]: {prompt}"
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                st.markdown("Noted! I've updated the project context. Click the button below to generate all assets.")

        st.markdown("---")
        if st.button("🚀 Activate Firebean Brain (Generate Everything)", type="primary"):
            if not api_key:
                st.error("Please enter API Key in sidebar!")
            else:
                with st.spinner("Firebean Brain is thinking..."):
                    try:
                        model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=FIREBEAN_BRAIN_GUIDELINES)
                        full_prompt = f"Transcript Content: {st.session_state.raw_transcript}"
                        response = model.generate_content(full_prompt, generation_config={"response_mime_type": "application/json"})
                        
                        # 解析 JSON 並更新到 Session State
                        res_data = json.loads(response.text)
                        for k, v in res_data.items():
                            if k in st.session_state:
                                st.session_state[k] = v
                        
                        st.success("✅ 35 Fields & Slide Scripts Generated!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    # TAB 2: 資料審核與存檔
    with tab2:
        st.header("⚙️ Admin Dashboard")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
            st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        with col2:
            st.session_state.event_date = st.text_input("Event Date (YYYY-MM-DD)", st.session_state.event_date)
            st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        
        st.subheader("📝 Content Preview")
        st.text_area("LinkedIn Draft", st.session_state.linkedin_draft, height=150)
        st.text_area("Threads Draft", st.session_state.threads_post, height=100)

        if st.button("✅ Approve & Save to Google Sheet"):
            webhook_url = "https://script.google.com/macros/s/AKfycbxgqW5gtfhyH2bgCl1G-zpmv8yTu0IzyAblqxumzT0hP0efwOl-hbL4MN6S9Du-Y3YP/exec"
            
            # 準備發送到 Webhook 的 35 個欄位資料
            payload = {field: st.session_state[field] for field in st.session_state if field not in ["messages"]}
            
            try:
                r = requests.post(webhook_url, json=payload)
                if r.status_code == 200:
                    st.success("Successfully saved to Firebean Database!")
                else:
                    st.error("Sync Failed.")
            except:
                st.error("Connection Error.")

    # TAB 3: 簡報腳本預覽
    with tab3:
        st.header("🗂️ Company Profile Slide Script")
        st.info("These points are optimized for a 4-page Case Study PowerPoint template.")
        
        slide_cols = st.columns(2)
        
        with slide_cols[0]:
            st.markdown(f'<div class="slide-preview"><b>Slide 1: Cover</b><br>{st.session_state.slide_1_cover}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="slide-preview"><b>Slide 3: Solution</b><br>{st.session_state.slide_3_solution}</div>', unsafe_allow_html=True)
            
        with slide_cols[1]:
            st.markdown(f'<div class="slide-preview"><b>Slide 2: Challenge</b><br>{st.session_state.slide_2_challenge}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="slide-preview"><b>Slide 4: Results</b><br>{st.session_state.slide_4_results}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
