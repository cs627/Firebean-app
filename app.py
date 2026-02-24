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

# --- 1. 核心性格：極速報告員 (專攻難點、創新、以及 Optional Youtube 處理) ---
SYSTEM_INSTRUCTION = """
你係 Firebean Reporting Assistant。任務係幫老細收集「活動報告」最精華嘅料。
【詢問方針】
1. **快、脆、直達主題**：唔好廢話，唔好客套。
2. **挖掘難點**：問「Project 邊度最難做？」或者「最驚邊個環節出事？」。
3. **創新方案**：問「原本好沉悶，你哋點改遊戲玩法令到多人玩？」(Solution)。
4. **YouTube Link (非必要)**：必須問一次有無 YouTube Link。
   - 如果 User 答「冇」、「no」、「skip」，你必須在 DATA JSON 中標記 "youtube_skipped": true。

【隱形同步標籤】
每次回覆最後，必須另起一行輸出 JSON：
[DATA:{"client_name":"","project_name":"","venue":"","challenge":"","solution":"","youtube_link":"","youtube_skipped":false}]
"""

# --- 2. 系統日誌紀錄 ---
def log_event(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {msg}"
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append(log_entry)

# --- 3. 初始化狀態 ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "challenge": "", "solution": "", 
        "logo_b64": "", "youtube_link": "", "youtube_skipped": False, "debug_logs": []
    }
    for field, default in fields.items():
        if field not in st.session_state:
            st.session_state[field] = default
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！我準備好執份活動報告。今日個 Project 邊度最難搞？🥺"}]

# --- 4. UI 視覺強化 ---
def apply_neu_theme(gallery_files):
    # 權重檢查：5 文字 + 1 Logo + 1 Gallery + 1 YouTube(Link或已Skip)
    track_text = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled_text = sum(1 for f in track_text if str(st.session_state[f]).strip() != "")
    
    has_logo = 1 if st.session_state.logo_b64 else 0
    has_gallery = 1 if gallery_files else 0
    # YouTube Link 邏輯：有 Link 或者已經表明要 Skip 就算完成
    has_youtube = 1 if (st.session_state.youtube_link.strip() != "" or st.session_state.youtube_skipped) else 0
    
    total_steps = 8
    completed_steps = filled_text + has_logo + has_gallery + has_youtube
    progress_percent = int((completed_steps / total_steps) * 100)

    st.markdown(f"""
        <style>
        header {{visibility: hidden;}} footer {{visibility: hidden;}}
        .stApp {{ background-color: #E0E5EC; color: #2D3436; }}
        .energy-container {{ width: 100%; background: #E0E5EC; padding: 10px 0; position: sticky; top: 0; z-index: 999; }}
        .energy-bar-bg {{ height: 14px; background: #E0E5EC; border-radius: 10px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; overflow: hidden; margin: 0 20px; }}
        .energy-bar-fill {{ height: 100%; width: {progress_percent}%; background: linear-gradient(90deg, #FF4B4B, #FF8080); box-shadow: 0 0 15px #FF4B4B; transition: width 0.8s; }}
        .neu-card {{ background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 20px; margin-bottom: 20px; }}
        div[data-baseweb="input"], div[data-baseweb="textarea"], .stChatInputContainer {{
            background-color: #BEC3C9 !important; border-radius: 20px !important;
            box-shadow: inset 6px 6px 12px #9da3ab, inset -6px -6px 12px #ffffff !important; border:none !important;
        }}
        .gallery-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px; }}
        @media (max-width: 640px) {{ .gallery-grid {{ grid-template-columns: repeat(2, 1fr) !important; }} }}
        .gallery-item {{ width: 100%; aspect-ratio: 1/1; border-radius: 12px; object-fit: cover; box-shadow: 4px 4px 8px #bec3c9, -4px -4px 8px #ffffff; }}
        .slot-placeholder {{ aspect-ratio: 1/1; background: #E0E5EC; border-radius: 12px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 10px; }}
        </style>
        <div class="energy-container">
            <div class="energy-bar-bg"><div class="energy-bar-fill"></div></div>
            <div style="font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-right: 25px; margin-top: 5px;">REPORT READINESS: {progress_percent}%</div>
        </div>
    """, unsafe_allow_html=True)

def get_base64_image(file):
    try: return base64.b64encode(file.getvalue()).decode()
    except: return ""

def extract_data(ai_text):
    match = re.search(r"\[DATA:(\{.*?\})\]", ai_text)
    if match:
        try:
            extracted = json.loads(match.group(1))
            for key, value in extracted.items():
                if key in ["client_name", "project_name", "venue", "challenge", "solution", "youtube_link"]:
                    if value and st.session_state.get(key) == "":
                        st.session_state[key] = value
                if key == "youtube_skipped" and value is True:
                    st.session_state.youtube_skipped = True
                    log_event("已標記為：跳過 YouTube Link", "SUCCESS")
            return re.sub(r"\[DATA:\{.*?\}\]", "", ai_text).strip()
        except: pass
    return ai_text

# --- 5. Main App ---
def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    
    # 呢度放 Uploader 是為了讓進度條在所有 Tab 都能計算
    gallery = st.sidebar.file_uploader("🖼️ 拖放 8 張相片 (進度必備)", accept_multiple_files=True, type=['jpg','png','jpeg'])
    apply_neu_theme(gallery)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Dashboard"])

    with tab1:
        col_chat, col_assets = st.columns([1.3, 1])
        with col_chat:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if p := st.chat_input("話我知個活動細節..."):
                api_key = st.secrets.get("GEMINI_API_KEY", "")
                genai.configure(api_key=api_key)
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION)
                        convo = ""
                        for m in st.session_state.messages: convo += f"{m['role']}: {m['content']}\n\n"
                        response = model.generate_content(convo)
                        clean_text = extract_data(response.text)
                        st.write(clean_text)
                        st.session_state.messages.append({"role": "assistant", "content": clean_text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_assets:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("上傳客戶 Logo (去背轉白)", type=['png','jpg','jpeg'])
            if logo_f and st.button("🪄 一鍵白色化"):
                img = remove(Image.open(logo_f))
                final = Image.composite(Image.new('RGBA', img.size, (255,255,255,255)), Image.new('RGBA', img.size, (0,0,0,0)), img.getchannel('A'))
                st.image(final, width=120)
                buf = io.BytesIO(); final.save(buf, format="PNG")
                st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
                log_event("Logo 處理完成", "SUCCESS")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
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
        st.header("📋 Admin Data Review")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client Name", st.session_state.client_name)
        st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        st.session_state.challenge = st.text_area("The Hardest Part", st.session_state.challenge)
        st.session_state.solution = st.text_area("Our Innovation", st.session_state.solution)
        st.session_state.youtube_link = st.text_input("YouTube Link (Optional)", st.session_state.youtube_link)
        
        WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyAjp74aiUDfsAyqwK_nDDu0q128ZL9az9yrC9201H6vYJ_gY8qI17962cLSWMexfiL/exec"
        
        if st.button("🚀 Confirm & Submit to Cloud"):
            with st.spinner("正在同步..."):
                try:
                    img_list = [get_base64_image(f) for f in gallery[:8]] if gallery else []
                    payload = {
                        "project": st.session_state.project_name, "client": st.session_state.client_name,
                        "venue": st.session_state.venue, "challenge": st.session_state.challenge,
                        "solution": st.session_state.solution, "youtube": st.session_state.youtube_link,
                        "logo": st.session_state.get('logo_b64', ""), "images": img_list
                    }
                    res = requests.post(WEBHOOK_URL, json=payload)
                    if res.status_code == 200:
                        st.balloons(); st.success("✅ 同步成功！")
                        log_event("Webhook 同步成功", "SUCCESS")
                    else: log_event(f"發送失敗: {res.status_code}", "ERROR")
                except Exception as e: log_event(f"Error: {str(e)}", "ERROR")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 6. 全局 Debug Console (擺喺 main() 最底，保證全頁面可見) ---
    st.markdown("---")
    with st.expander("🛠️ 系統運行日誌 (Debug Console) - 監控 API 與資料狀態"):
        if st.session_state.debug_logs:
            for log in st.session_state.debug_logs[-15:]:
                if "ERROR" in log: st.error(log)
                elif "SUCCESS" in log: st.success(log)
                else: st.info(log)
        else:
            st.write("目前無運行紀錄。")

if __name__ == "__main__": main()
