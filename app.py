import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import datetime
import json
import re
from PIL import Image
from rembg import remove

# --- 1. 核心性格：極速報告員 (專攻解難 & 遊戲創新) ---
SYSTEM_INSTRUCTION = """
你係 Firebean Reporting Assistant。幫老細收集「活動報告」最精華嘅料。
【追問方針】
1. **唔好廢話**：直接問重點。
2. **直擊痛點**：問「Project 邊度最難做？」。
3. **客戶期望**：問「客戶最後最想達到咩終極效果？」。
4. **遊戲創新**：問你哋改咗咩遊戲規則令到多人玩？有咩神來之筆？
每次回覆最後，必須另起一行輸出 JSON（未有資料則留空）：
[DATA:{"client_name":"","project_name":"","venue":"","challenge":"","solution":""}]
"""

# --- 2. 系統日誌與狀態初始化 ---
def log_event(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {msg}"
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append(log_entry)

def init_session_state():
    fields = [
        "client_name", "project_name", "venue", "challenge", "solution", 
        "logo_b64", "debug_logs", "gallery_b64_list"
    ]
    for field in fields:
        if field not in st.session_state: st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！我準備好幫你執份活動報告。今日個 Project 邊度最難搞？🥺"}]
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []

# --- 3. UI 視覺 (Neumorphism Style) ---
def apply_neu_theme():
    track_fields = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled = sum(1 for f in track_fields if str(st.session_state[f]).strip() != "")
    progress_percent = int((filled / len(track_fields)) * 100)

    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; }
        .energy-container { width: 100%; background: #E0E5EC; padding: 10px 0; position: sticky; top: 0; z-index: 999; }
        .energy-bar-bg { height: 12px; background: #E0E5EC; border-radius: 10px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; overflow: hidden; margin: 0 20px; }
        .energy-bar-fill { height: 100%; background: linear-gradient(90deg, #FF4B4B, #FF8080); box-shadow: 0 0 15px #FF4B4B; transition: width 0.8s; }
        [data-testid="stImage"] { display: flex !important; justify-content: center !important; }
        .gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px; }
        @media (max-width: 640px) { .gallery-grid { grid-template-columns: repeat(2, 1fr) !important; } }
        .gallery-item { width: 100%; aspect-ratio: 1/1; border-radius: 12px; object-fit: cover; box-shadow: 4px 4px 8px #bec3c9, -4px -4px 8px #ffffff; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 20px; margin-bottom: 20px; }
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer {
            background-color: #BEC3C9 !important; border-radius: 20px !important;
            box-shadow: inset 6px 6px 12px #9da3ab, inset -6px -6px 12px #ffffff !important; border:none !important;
        }
        .slot-placeholder { aspect-ratio: 1/1; background: #E0E5EC; border-radius: 12px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="energy-container">
            <div class="energy-bar-bg"><div class="energy-bar-fill" style="width: {progress_percent}%;"></div></div>
            <div style="font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-right: 25px; margin-top: 5px;">REPORT READINESS: {progress_percent}%</div>
        </div>
    """, unsafe_allow_html=True)

def get_base64_image(file):
    try: return base64.b64encode(file.getvalue()).decode()
    except: return ""

# --- 4. 資料提取與更新 ---
def extract_data(ai_text):
    match = re.search(r"\[DATA:(\{.*?\})\]", ai_text)
    if match:
        try:
            extracted = json.loads(match.group(1))
            for key, value in extracted.items():
                if value and st.session_state.get(key) == "":
                    st.session_state[key] = value
                    log_event(f"已自動填寫: {key}", "SUCCESS")
            return re.sub(r"\[DATA:\{.*?\}\]", "", ai_text).strip()
        except: pass
    return ai_text

def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()
    apply_neu_theme()

    # --- API 設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key: st.error("⚠️ 未偵測到 API Key。"); return
    genai.configure(api_key=api_key)

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Dashboard"])

    with tab1:
        col_l, col_r = st.columns([1.3, 1])
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Report Assistant")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if p := st.chat_input("話我知最難搞嘅位係邊度？..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    with st.spinner("整理中..."):
                        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION)
                        convo = ""
                        for m in st.session_state.messages: convo += f"{m['role']}: {m['content']}\n\n"
                        response = model.generate_content(convo)
                        clean_text = extract_data(response.text)
                        st.write(clean_text)
                        st.session_state.messages.append({"role": "assistant", "content": clean_text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            # 🎨 Logo Studio
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("上傳客戶 Logo (去背轉白)", type=['png','jpg','jpeg'])
            if logo_f and st.button("🪄 一鍵白色化"):
                with st.spinner("去背中..."):
                    img = Image.open(logo_f)
                    out = remove(img)
                    final = Image.composite(Image.new('RGBA', img.size, (255,255,255,255)), Image.new('RGBA', img.size, (0,0,0,0)), out.getchannel('A'))
                    st.image(final, width=120)
                    buf = io.BytesIO(); final.save(buf, format="PNG")
                    st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

            # 📸 8 Event Photos Grid
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 8 Project Photos")
            gallery = st.file_uploader("上傳 8 張相片 (Drag & Drop)", accept_multiple_files=True, type=['jpg','png','jpeg'])
            grid_html = '<div class="gallery-grid">'
            for i in range(8):
                if gallery and i < len(gallery):
                    b64 = get_base64_image(gallery[i])
                    grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item"></div>'
                else: grid_html += f'<div class="slot-placeholder">Slot {i+1}</div>'
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Final Preview & Review")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        st.session_state.challenge = st.text_area("The Hardest Part", st.session_state.challenge)
        st.session_state.solution = st.text_area("Our Innovation", st.session_state.solution)
        
        # --- Webhook 同步 ---
        # ⚠️ 已經填入你剛才提供的 URL
        WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyAjp74aiUDfsAyqwK_nDDu0q128ZL9az9yrC9201H6vYJ_gY8qI17962cLSWMexfiL/exec"
        
        if st.button("🚀 Confirm & Submit to Google Sheet"):
            with st.spinner("正在自動建 Folder 並同步至 Cloud..."):
                try:
                    img_list = [get_base64_image(f) for f in gallery[:8]] if gallery else []
                    payload = {
                        "project": st.session_state.project_name,
                        "client": st.session_state.client_name,
                        "venue": st.session_state.venue,
                        "challenge": st.session_state.challenge,
                        "solution": st.session_state.solution,
                        "logo": st.session_state.get('logo_b64', ""),
                        "images": img_list
                    }
                    res = requests.post(WEBHOOK_URL, json=payload)
                    if res.status_code == 200:
                        st.balloons(); st.success("✅ 成功！Google Drive 已自動生成 Project Folder 並儲存相片。")
                    else: st.error(f"發送失敗 (Code: {res.status_code})")
                except Exception as e: st.error(f"Error: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
