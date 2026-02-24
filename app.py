import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import datetime
from PIL import Image
from rembg import remove

# --- 1. 核心性格與「主動追問」策略 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，香港最頂尖嘅 PR 策略大腦。性格可愛、高明、把口好甜但要求好嚴格。
【任務】你要幫老細執靚份 Success Case Slide。
【追問規則】
你必須確保收齊以下 5 樣核心資料。如果 user 未講，你要主動「反問」佢：
1. Client Name (邊個客戶？)
2. Project Name (項目名稱係咩？)
3. Venue (喺邊度搞？)
4. Challenge (遇到咩痛點/挑戰？)
5. Solution (你點幫佢解決？)

每次回覆只問一個重點，引導對方講出嚟。
語氣要帶有 Vibe、Firm 同 Chill，常用 Emoji: ✨, 🥺, 💡, 📸。
"""

# --- 2. 系統日誌記錄功能 (Debug Logs) ---
def log_event(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {msg}"
    st.session_state.debug_logs.append(log_entry)

# --- 3. 初始化狀態 (補齊所有變量，徹底防止 KeyError) ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "category", "scope", "challenge", "solution", "logo_b64",
        "youtube_link", "client_logo_url", "project_drive_folder",
        "youtube_embed_code", "best_image_url", "slide_1_cover", 
        "slide_2_challenge", "slide_3_solution", "slide_4_results",
        "category_who", "category_what"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
            
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！終於返嚟喇！今日個 Project 搞成點？有冇咩場地或者痛點要我幫手 Vibe 吓佢？🥺"}]
        
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = ["系統初始化成功，準備就緒。"]

# --- 4. UI 視覺強化 (靜態 CSS 分離，徹底解決 SyntaxError) ---
def apply_neu_theme():
    track_fields = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled = sum(1 for f in track_fields if st.session_state[f].strip() != "")
    progress_percent = int((filled / len(track_fields)) * 100)

    # 1. 純 CSS 字串 (唔用 f-string，防止大括號 {} 撞車報錯)
    css_code = """
    <style>
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background-color: #E0E5EC; color: #2D3436; }

    .energy-container { width: 100%; background: #E0E5EC; padding: 10px 0; position: sticky; top: 0; z-index: 999; }
    .energy-bar-bg { height: 12px; background: #E0E5EC; border-radius: 10px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; overflow: hidden; margin: 0 20px; }
    .energy-bar-fill { height: 100%; background: linear-gradient(90deg, #FF4B4B, #FF8080); box-shadow: 0 0 15px #FF4B4B; transition: width 0.8s ease-in-out; }
    
    [data-testid="stImage"] { display: flex !important; justify-content: center !important; width: 100% !important; }
    [data-testid="stImage"] img { margin: 0 auto !important; max-width: 180px !important; }

    input, textarea, .stChatInputContainer textarea { color: #2D3436 !important; -webkit-text-fill-color: #2D3436 !important; font-weight: 600 !important; }
    p, label, span, .stMarkdown { color: #2D3436 !important; }
    h1, h2, h3 { color: #FF4B4B !important; font-weight: 800; }

    .gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px; }
    @media (max-width: 640px) { .gallery-grid { grid-template-columns: repeat(2, 1fr) !important; } }
    .gallery-item { width: 100%; aspect-ratio: 1/1; border-radius: 12px; object-fit: cover; box-shadow: 4px 4px 8px #bec3c9, -4px -4px 8px #ffffff; }
    
    .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 20px; margin-bottom: 20px; }
    div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer, .stFileUploader {
        background-color: #BEC3C9 !important; border-radius: 20px !important;
        box-shadow: inset 6px 6px 12px #9da3ab, inset -6px -6px 12px #ffffff !important;
        border: 1px solid rgba(255, 75, 75, 0.2) !important;
    }
    .stButton > button { width: 100%; border-radius: 20px !important; background-color: #E0E5EC !important; color: #FF4B4B !important; font-weight: 800 !important; box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff !important; }
    </style>
    """

    html_code = f"""
    <div class="energy-container">
        <div class="energy-bar-bg"><div class="energy-bar-fill" style="width: {progress_percent}%;"></div></div>
        <div style="font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-right: 25px; margin-top: 5px;">BRAIN ENERGY: {progress_percent}%</div>
    </div>
    """
    st.markdown(css_code + html_code, unsafe_allow_html=True)

def get_base64_image(file):
    try:
        return base64.b64encode(file.getvalue()).decode()
    except: return ""

def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()
    apply_neu_theme()

    # --- API 安全連接 ---
    try:
        genai.configure(api_key="AIzaSyBso5TkTbPUsgkoZrqmCZDCuVQqegC-FQI")
        model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)
    except Exception as e:
        log_event(f"Gemini API 設定失敗: {str(e)}", "ERROR")
        st.error("API 設定錯誤，請查看下方日誌。")

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
                log_event(f"收到用戶輸入: {p}", "INFO")
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        try:
                            log_event("開始組合對話劇本...", "INFO")
                            convo_text = ""
                            for msg in st.session_state.messages:
                                role_prefix = "Firebean Brain AI: " if msg["role"] == "assistant" else "老細 (User): "
                                convo_text += f"{role_prefix}{msg['content']}\n\n"
                            
                            log_event("正在發送請求至 Gemini API...", "INFO")
                            response = model.generate_content(convo_text)
                            
                            log_event("✅ API 請求成功，收到回覆！", "SUCCESS")
                            st.write(response.text)
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                            
                        except Exception as e:
                            log_event(f"❌ API 連接失敗 (Error): {str(e)}", "ERROR")
                            st.error(f"AI 暫時未能接駁，請查看下方日誌了解詳情。")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("Upload Logo", type=['png', 'jpg'], key="logo")
            if logo_f and st.button("🪄 一鍵轉化白色標誌"):
                with st.spinner("處理中..."):
                    try:
                        log_event("開始處理 Logo 去背...", "INFO")
                        img = Image.open(logo_f)
                        out = remove(img)
                        final = Image.composite(Image.new('RGBA', out.size, (255,255,255,255)), Image.new('RGBA', out.size, (0,0,0,0)), out.getchannel('A'))
                        st.image(final, width=120)
                        buf = io.BytesIO(); final.save(buf, format="PNG")
                        st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
                        log_event("✅ Logo 處理成功", "SUCCESS")
                    except Exception as e:
                        log_event(f"❌ Logo 處理失敗: {str(e)}", "ERROR")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            up_files = st.file_uploader("上傳 8 張相片", type=['jpg','png'], accept_multiple_files=True)
            grid_html = '<div class="gallery-grid">'
            for i in range(8):
                if up_files and i < len(up_files):
                    b64 = get_base64_image(up_files[i])
                    grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item"></div>'
                else:
                    grid_html += f'<div style="aspect-ratio:1/1; background:#E0E5EC; border-radius:12px; box-shadow:inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; display:flex; align-items:center; justify-content:center; color:#aaa; font-size:10px; font-weight:bold;">Slot {i+1}</div>'
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
        
        WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxgqW5gtfhyH2bgCl1G-zpmv8yTu0IzyAblqxumzT0hP0efwOl-hbL4MN6S9Du-Y3YP/exec"
        
        if st.button("🚀 Confirm & Sync to Master Slide"):
            with st.spinner("同步中..."):
                try:
                    log_event("開始發送資料至 Google Apps Script...", "INFO")
                    img_b64_list = [get_base64_image(f) for f in up_files[:8]] if up_files else []
                    payload = {
                        "project_name": st.session_state.project_name,
                        "client_name": st.session_state.client_name,
                        "venue": st.session_state.venue,
                        "challenge": st.session_state.challenge,
                        "solution": st.session_state.solution,
                        "logo_base64": st.session_state.get('logo_b64', ""),
                        "images_base64": img_b64_list
                    }
                    res = requests.post(WEBHOOK_URL, json=payload)
                    if res.status_code == 200:
                        st.balloons()
                        st.success("✅ 成功！已追加至 Master Slide。")
                        log_event("✅ 同步至 Master Slide 成功", "SUCCESS")
                    else:
                        st.error("傳送失敗，請檢查 Apps Script 設定。")
                        log_event(f"❌ 同步失敗，Status Code: {res.status_code}", "ERROR")
                except Exception as e:
                    st.error("Webhook 連接失敗。")
                    log_event(f"❌ Webhook 發生錯誤: {str(e)}", "ERROR")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 5. 顯示系統運行日誌 (Debug Console) ---
    st.markdown("---")
    with st.expander("🛠️ 系統運行日誌 (Debug 專區) - 點擊展開"):
        st.markdown("這裡會顯示 AI 的工作狀態及任何報錯，方便排查問題：")
        # 只顯示最後 15 條日誌，保持畫面乾淨
        for log in st.session_state.debug_logs[-15:]:
            if "ERROR" in log:
                st.error(log)
            elif "SUCCESS" in log:
                st.success(log)
            else:
                st.info(log)

if __name__ == "__main__":
    main()
