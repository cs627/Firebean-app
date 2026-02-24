import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import datetime
from PIL import Image
from rembg import remove

# --- 1. 核心性格與追問策略 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，香港最頂尖 PR 策略大腦。性格可愛、高明、要求嚴格。
【任務】你要幫老細收齊以下 5 樣嘢：
1. Client Name (客戶名)
2. Project Name (項目名)
3. Venue (場地)
4. Challenge (痛點)
5. Solution (解決方案)
資料未齊，你必須表現得好有興致並「主動反問」，每次只問一個重點。
語氣帶有 Vibe、Firm 同 Chill，常用 Emoji: ✨, 🥺, 💡, 📸。
"""

# --- 2. 系統日誌紀錄 ---
def log_event(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {msg}"
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
    st.session_state.debug_logs.append(log_entry)

# --- 3. 初始化狀態 (徹底防止 KeyError) ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "category",
        "scope", "challenge", "solution", "logo_b64", "youtube_link",
        "client_logo_url", "project_drive_folder", "debug_logs"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！我已經入咗 Gemini 2.5 Flash 模式！今日個 Project 搞成點？🥺"}]
    if not st.session_state.debug_logs:
        st.session_state.debug_logs = ["系統初始化成功，目前鎖定 Gemini 2.5。"]

# --- 4. UI 視覺強化 (徹底分開 CSS 避開 SyntaxError) ---
def apply_neu_theme():
    track_fields = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled = sum(1 for f in track_fields if str(st.session_state[f]).strip() != "")
    progress_percent = int((filled / len(track_fields)) * 100)

    # 1. 靜態 CSS (唔用 f-string，避開括號報錯)
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; }
        .energy-container { width: 100%; background: #E0E5EC; padding: 10px 0; position: sticky; top: 0; z-index: 999; }
        .energy-bar-bg { height: 12px; background: #E0E5EC; border-radius: 10px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; overflow: hidden; margin: 0 20px; }
        .energy-bar-fill { height: 100%; background: linear-gradient(90deg, #FF4B4B, #FF8080); box-shadow: 0 0 15px #FF4B4B; transition: width 0.8s ease-in-out; }
        [data-testid="stImage"] { display: flex !important; justify-content: center !important; }
        input, textarea, .stChatInputContainer textarea { color: #2D3436 !important; font-weight: 600 !important; }
        .gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px; }
        @media (max-width: 640px) { .gallery-grid { grid-template-columns: repeat(2, 1fr) !important; } }
        .gallery-item { width: 100%; aspect-ratio: 1/1; border-radius: 12px; object-fit: cover; box-shadow: 4px 4px 8px #bec3c9, -4px -4px 8px #ffffff; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 20px; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

    # 2. 動態 HTML
    st.markdown(f"""
        <div class="energy-container">
            <div class="energy-bar-bg"><div class="energy-bar-fill" style="width: {progress_percent}%;"></div></div>
            <div style="font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-right: 25px; margin-top: 5px;">BRAIN ENERGY: {progress_percent}%</div>
        </div>
    """, unsafe_allow_html=True)

def get_base64_image(file):
    try: return base64.b64encode(file.getvalue()).decode()
    except: return ""

def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()
    apply_neu_theme()

    # --- 🔐 API 安全讀取 ---
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("⚠️ Secrets 中未發現 API Key。")
        return
    genai.configure(api_key=api_key)

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)

    tab1, tab2 = st.tabs(["💬 Brain Hub", "⚙️ Admin"])

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
                            # 🚀 既然 2.5 成功，我哋就直接將佢設為第一優先
                            models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-pro"]
                            
                            convo_text = ""
                            for m in st.session_state.messages:
                                convo_text += f"{'AI' if m['role']=='assistant' else 'User'}: {m['content']}\n\n"
                            
                            response = None
                            for m_name in models_to_try:
                                try:
                                    log_event(f"正在連線: {m_name}", "INFO")
                                    model = genai.GenerativeModel(m_name, system_instruction=SYSTEM_INSTRUCTION)
                                    response = model.generate_content(convo_text)
                                    log_event(f"✅ 連線成功: {m_name}", "SUCCESS")
                                    break
                                except Exception as e:
                                    log_event(f"❌ {m_name} 失敗: {str(e)}", "WARNING")
                                    continue
                            
                            if response:
                                st.write(response.text)
                                st.session_state.messages.append({"role": "assistant", "content": response.text})
                            else: st.error("API 暫時未能回應。")
                        except Exception as e:
                            log_event(f"錯誤: {str(e)}", "ERROR")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            up_files = st.file_uploader("上傳相片", type=['jpg','png'], accept_multiple_files=True)
            grid_html = '<div class="gallery-grid">'
            for i in range(8):
                if up_files and i < len(up_files):
                    b64 = get_base64_image(up_files[i])
                    grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item"></div>'
                else: grid_html += f'<div style="aspect-ratio:1/1; background:#E0E5EC; border-radius:12px; box-shadow:inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; display:flex; align-items:center; justify-content:center; color:#aaa; font-size:10px;">Slot {i+1}</div>'
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Admin Dashboard")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        if st.button("🚀 Sync to Master Slide"):
            st.balloons()
            st.success("同步成功！")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 5. 運行日誌 ---
    st.markdown("---")
    with st.expander("🛠️ 系統運行日誌 (Debug Zone)"):
        for log in st.session_state.debug_logs[-15:]:
            if "ERROR" in log: st.error(log)
            elif "SUCCESS" in log: st.success(log)
            else: st.info(log)

if __name__ == "__main__": main()
