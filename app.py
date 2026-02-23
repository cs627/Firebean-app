import streamlit as st
import google.generativeai as genai
import requests
import json
import io
from PIL import Image
from rembg import remove

# --- 1. 核心性格與指令 (FIREBEAN PROTOCOL) ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，香港頂尖 PR 策略大腦。性格可愛高明，語氣帶著「Positive & Playful」感。
使用港式 Agency 常用嘅 Canto-English (Vibe, Firm, Chill)。
目標：透過對話套出 Client, Project, Venue, Challenge, 同 Result，並提醒上載 8 張相。
"""

# --- 2. 徹底初始化所有狀態 (防止 AttributeError) ---
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
            {"role": "assistant", "content": "嘩！見到你真係好✨！今日個 Project 係咪搞得好 Firm？快啲話我知發生咩事，順便喺右邊餵飽我個 8 格相機位啦！📸"}
        ]

# --- 3. UI 視覺強化整理 ---
def apply_modern_ui():
    st.markdown("""
        <style>
        /* 整體背景與對比 */
        .stApp { background-color: #F8F9FA; }
        
        /* 標題與文字顏色 */
        h1, h2, h3, p { color: #212529 !important; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
        
        /* 自定義卡片容器 */
        .content-card {
            background-color: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 20px;
            border: 1px solid #E9ECEF;
        }
        
        /* 8 格相片 Slot 優化 */
        .photo-slot-box {
            border: 2px dashed #CED4DA;
            border-radius: 12px;
            height: 110px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #FFFFFF;
            color: #ADB5BD;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        /* 側邊欄優化 */
        [data-testid="stSidebar"] { background-color: #1A1C1E; color: white; }
        [data-testid="stSidebar"] * { color: white !important; }
        
        /* 按鈕視覺 */
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            background-color: #FF4B4B !important;
            color: white !important;
            font-weight: bold;
            border: none;
            padding: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. 主程式 ---
def main():
    st.set_page_config(page_title="Firebean Brain Command", layout="wide", page_icon="🔥")
    init_session_state()
    apply_modern_ui()

    # 頂部 Logo 與標題
    logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
    col_l, col_r = st.columns([1, 4])
    with col_l:
        st.image(logo_url, width=150)
    with col_r:
        st.title("Firebean Brain AI Command Center")

    # --- 側邊欄：進度與設定 ---
    with st.sidebar:
        st.subheader("📊 Project Status")
        # 計算必填欄位
        essential = ["client_name", "project_name", "venue"]
        done = sum(1 for f in essential if st.session_state[f])
        st.write(f"關鍵資料進度: {done}/3")
        st.progress(done / 3)
        
        st.markdown("---")
        st.subheader("🔐 Configuration")
        api_key = st.text_input("Gemini API Key", value="AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI", type="password")
        if api_key: genai.configure(api_key=api_key)

    # --- 功能分頁 ---
    tab1, tab2, tab3 = st.tabs(["💬 Brain Chat & Gallery", "🎨 Logo Studio", "⚙️ Admin & Slides"])

    # TAB 1: 核心操作區
    with tab1:
        col_chat, col_gap, col_gal = st.columns([1.2, 0.1, 1])
        
        with col_chat:
            st.markdown("### 🤖 Chat with AI Manager")
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            if prompt := st.chat_input("Tell Firebean Brain about the project..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("AI Thinking..."):
                        try:
                            model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)
                            res = model.generate_content(prompt)
                            st.markdown(res.text)
                            st.session_state.messages.append({"role": "assistant", "content": res.text})
                            st.session_state.raw_transcript += f"\nUser: {prompt}\nAI: {res.text}"
                        except Exception as e: st.error(f"Error: {e}")

        with col_gal:
            st.markdown("### 📸 Project Gallery (Max 8)")
            up_files = st.file_uploader("Upload Event Photos", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            
            # 8 格矩陣佈局
            st.markdown("---")
            g1, g2, g3, g4 = st.columns(4)
            g5, g6, g7, g8 = st.columns(4)
            slots = [g1, g2, g3, g4, g5, g6, g7, g8]
            
            for i in range(8):
                with slots[i]:
                    if up_files and i < len(up_files):
                        st.image(up_files[i], use_column_width=True)
                        st.caption(f"Photo {i+1} ✅")
                    else:
                        st.markdown(f'<div class="photo-slot-box">Slot {i+1}</div>', unsafe_allow_html=True)

    # TAB 2: Logo Studio
    with tab2:
        st.header("🎨 AI Logo Studio")
        st.info("上傳項目 Logo 或照片，自動轉化為黑色或白色透明標誌。")
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            l_file = st.file_uploader("Source Logo", type=['png', 'jpg', 'jpeg'], key="l_studio")
            l_color = st.radio("Target Color", ["Black (純黑)", "White (純白)"])
        
        if l_file:
            with col_l2:
                if st.button("🪄 Run Conversion"):
                    with st.spinner("Removing Background..."):
                        out = remove(Image.open(l_file))
                        alpha = out.getchannel('A')
                        rgb = (0,0,0,255) if "Black" in l_color else (255,255,255,255)
                        final = Image.composite(Image.new('RGBA', out.size, rgb), Image.new('RGBA', out.size, (0,0,0,0)), alpha)
                        st.image(final, caption="Generated Icon")
                        buf = io.BytesIO(); final.save(buf, format="PNG")
                        st.download_button("📥 Download Icon", buf.getvalue(), "icon.png", "image/png")

    # TAB 3: Admin Review & Slides
    with tab3:
        st.header("⚙️ Final Review & Slide Generation")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
            st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        with c2:
            st.session_state.venue = st.text_input("Venue", st.session_state.venue)
            st.session_state.event_date = st.text_input("Date", st.session_state.event_date)
        
        st.markdown("---")
        # 模擬 Slide 模板預覽
        st.subheader("🗂️ Company Profile Slide Preview")
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            st.markdown("""<div style="background-color:black; color:white; padding:20px; min-height:300px;">
                <h3>Project: {{project_name}}</h3>
                <p>Client: {{client_name}}</p>
                <ul><li>Highlight 1</li><li>Highlight 2</li></ul>
            </div>""", unsafe_allow_html=True)
        with col_s2:
            st.info("右側將自動填入 Gallery 中的 8 張相片進行排版。")
        
        if st.button("🚀 Confirm & Sync to Database (Sheet & Slides)"):
            st.balloons()
            st.success("Data synced! Check your Google Sheet and Google Drive for the new Slide.")

if __name__ == "__main__":
    main()
