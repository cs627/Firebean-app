import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import datetime
from PIL import Image
from rembg import remove

# --- 1. 核心性格 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，香港最頂尖 PR 策略大腦。
你嘅目標係透過對話套出：Client Name, Project Name, Venue, Challenge, 同 Solution。
如果資料未齊，你必須主動「反問」對方，引導佢講埋其餘部分。
每次回覆只問一個重點。語氣要帶有 Vibe、Firm 同 Chill，常用 Emoji: ✨, 🥺, 💡, 📸。
"""

# --- 2. 日誌紀錄 ---
def log_event(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {msg}"
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
    st.session_state.debug_logs.append(log_entry)

# --- 3. 初始化狀態 ---
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
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！我準備好幫你執靚份 Profile，話我知今日個 Project 搞成點？🥺"}]
    if not st.session_state.debug_logs:
        st.session_state.debug_logs = ["系統初始化成功。"]

# --- 4. UI 視覺強化 (徹底修復 SyntaxError) ---
def apply_neu_theme():
    track_fields = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled = sum(1 for f in track_fields if str(st.session_state[f]).strip() != "")
    progress_percent = int((filled / len(track_fields)) * 100)

    # 靜態 CSS (不含變量，避開大括號解析錯誤)
    st.markdown("""
        <style>
        header {visibility: hidden;}
        footer {visibility: hidden;}
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
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, .stFileUploader {
            background-color: #BEC3C9 !important; border-radius: 20px !important;
            box-shadow: inset 6px 6px 12px #9da3ab, inset -6px -6px 12px #ffffff !important;
            border: 1px solid rgba(255, 75, 75, 0.2) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 動態進度條 HTML
    st.markdown(f"""
        <div class="energy-container">
            <div class="energy-bar-bg"><div class="energy-bar-fill" style="width: {progress_percent}%;"></div></div>
            <div style="font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-right: 25px; margin-top: 5px;">BRAIN ENERGY: {progress_percent}%</div>
        </div>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()
    apply_neu_theme()

    # --- API 安全連接 (優先從 Secrets 讀取) ---
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key:
            st.warning("⚠️ 尚未偵測到 API Key。請在 Streamlit Secrets 中設置 'GEMINI_API_KEY'。")
            return
        genai.configure(api_key=api_key)
    except Exception as e:
        log_event(f"API 配置出錯: {str(e)}", "ERROR")

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)

    tab1, tab2 = st.tabs(["💬 Brain Hub", "⚙️ Admin & Sync"])

    with tab1:
        col_l, col_r = st.columns([1.3, 1])
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean Assistant")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if p := st.chat_input("傾吓個 Project..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        try:
                            # 模型選擇列表 (Model Fallback)
                            # 優先使用截圖顯示的最新型號
                            models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
                            
                            convo_text = ""
                            for m in st.session_state.messages:
                                convo_text += f"{'AI' if m['role']=='assistant' else 'User'}: {m['content']}\n\n"
                            
                            response = None
                            for m_name in models_to_try:
                                try:
                                    log_event(f"嘗試連接: {m_name}", "INFO")
                                    model = genai.GenerativeModel(m_name, system_instruction=SYSTEM_INSTRUCTION)
                                    response = model.generate_content(convo_text)
                                    log_event(f"✅ 成功連線: {m_name}", "SUCCESS")
                                    break
                                except Exception as e:
                                    log_event(f"❌ 模型 {m_name} 失敗: {str(e)}", "WARNING")
                                    continue
                            
                            if response:
                                st.write(response.text)
                                st.session_state.messages.append({"role": "assistant", "content": response.text})
                            else:
                                st.error("抱歉，目前所有模型都無法回應，可能 API Key 權限不足或已爆配額。")
                        except Exception as e:
                            log_event(f"系統錯誤: {str(e)}", "ERROR")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("Upload Logo", type=['png', 'jpg'], key="logo")
            if logo_f and st.button("🪄 轉化白色標誌"):
                with st.spinner("處理中..."):
                    img = remove(Image.open(logo_f))
                    final = Image.composite(Image.new('RGBA', img.size, (255,255,255,255)), Image.new('RGBA', img.size, (0,0,0,0)), img.getchannel('A'))
                    st.image(final, width=120)
                    buf = io.BytesIO(); final.save(buf, format="PNG")
                    st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Admin Dashboard")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        st.session_state.challenge = st.text_area("Challenge", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution", st.session_state.solution)
        if st.button("🚀 Confirm & Sync"):
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

if __name__ == "__main__":
    main()
