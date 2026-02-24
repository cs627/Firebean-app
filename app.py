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

# --- 1. 核心性格：專業報告分析員 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Reporting Brain。你嘅唯一任務係：幫老細收集「活動報告」最關鍵嘅料。
【追問方針】
1. **唔好客套**，唔好吹捧。直接入主題問重點。
2. **挖掘難點**：要問「成個 Project 邊度最難做？」或者「最驚邊個環節出事？」。
3. **客戶期望**：問「客戶最希望達到咩效果？」(Client's Goal)。
4. **遊戲創新 (Solution)**：如果原本好沉悶，你哋改咗咩遊戲規則令到多人玩？點樣解決個難題？
5. **對話導向**：唔好一齊諗宣傳，要集中收返「發生咗咩事」同「你點解決」。

【隱形同步指令】
每次回覆嘅最後，你必須另起一行，用 JSON 格式更新已識別嘅欄位（未有就留空）：
[DATA:{"client_name":"","project_name":"","venue":"","challenge":"","solution":""}]
"""

# --- 2. 系統日誌 ---
def log_event(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {msg}"
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append(log_entry)

# --- 3. 初始化狀態 ---
def init_session_state():
    fields = [
        "client_name", "project_name", "venue", "challenge", "solution", 
        "logo_b64", "debug_logs"
    ]
    for field in fields:
        if field not in st.session_state: st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細，今日個 Project 有咩最難搞嘅位？個客最後最想達成咩效果？"}]
    if not st.session_state.debug_logs: st.session_state.debug_logs = ["系統就緒。"]

# --- 4. 自動提取器 (即時更新 Admin & 進度條) ---
def extract_and_update_data(ai_text):
    try:
        # 搵出 [DATA:...] 標籤
        match = re.search(r"\[DATA:(\{.*?\})\]", ai_text)
        if match:
            json_str = match.group(1)
            extracted_data = json.loads(json_str)
            for key, value in extracted_data.items():
                # 只有當目前係空值，且 AI 有新資料時先填入
                if value and st.session_state.get(key) == "":
                    st.session_state[key] = value
                    log_event(f"已自動填寫: {key}", "SUCCESS")
            # 清除 AI 回覆入面嘅 JSON 碼，唔畀 User 見到
            clean_text = re.sub(r"\[DATA:\{.*?\}\]", "", ai_text).strip()
            return clean_text
    except Exception as e:
        log_event(f"提取出錯: {str(e)}", "WARNING")
    return ai_text

# --- 5. UI 視覺 (Neumorphism Style) ---
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
        .energy-bar-fill { height: 100%; background: linear-gradient(90deg, #FF4B4B, #FF8080); box-shadow: 0 0 15px #FF4B4B; transition: width 0.8s ease-in-out; }
        input, textarea, .stChatInputContainer textarea { color: #2D3436 !important; font-weight: 600 !important; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 20px; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="energy-container">
            <div class="energy-bar-bg"><div class="energy-bar-fill" style="width: {progress_percent}%;"></div></div>
            <div style="font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-right: 25px; margin-top: 5px;">REPORT COMPLETION: {progress_percent}%</div>
        </div>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain 2.5", layout="wide")
    init_session_state()
    apply_neu_theme()

    # --- API 安全連接 ---
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("⚠️ 未設置 API Key。")
        return
    genai.configure(api_key=api_key)

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)

    tab1, tab2 = st.tabs(["💬 收料中心 (Collector)", "📋 報告預覽 (Admin)"])

    with tab1:
        col_l, col_r = st.columns([1.3, 1])
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if p := st.chat_input("話我知個活動細節..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                
                with st.chat_message("assistant"):
                    with st.spinner("AI 整理資料中..."):
                        try:
                            # 鎖定 Gemini 2.5 Flash
                            model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION)
                            convo = ""
                            for m in st.session_state.messages:
                                convo += f"{'AI' if m['role']=='assistant' else 'User'}: {m['content']}\n\n"
                            
                            response = model.generate_content(convo)
                            # 🚀 隱形同步：提取 JSON 並更新
                            display_text = extract_and_update_data(response.text)
                            
                            st.write(display_text)
                            st.session_state.messages.append({"role": "assistant", "content": display_text})
                        except Exception as e:
                            log_event(f"Error: {str(e)}", "ERROR")
                st.rerun() # 強制刷新畫面以更新進度條
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 活動紀錄")
            st.file_uploader("Upload Photos", accept_multiple_files=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 報告資料確認")
        st.session_state.project_name = st.text_input("Project Name (活動名)", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client Name (客戶名)", st.session_state.client_name)
        st.session_state.venue = st.text_input("Venue (地點)", st.session_state.venue)
        st.session_state.challenge = st.text_area("The Hardest Part (最大難題)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Innovation (解決方案/點解變好玩)", st.session_state.solution)
        
        if st.button("🚀 生成最終報告"):
            st.balloons()
            st.success("報告資料已就緒！")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
