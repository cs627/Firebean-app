import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import json
import re
from PIL import Image
from rembg import remove

# --- 1. SOW 選項清單 (已加入 Concept development) ---
SOW_OPTIONS = [
    "Overall planning and coordination",
    "Event Production / Theme Development",
    "Concept development",
    "Social Media Management",
    "KOL 網紅",
    "Media Pitching",
    "Interactive Game preparation",
    "Theme design"
]

# --- 2. 核心性格：聰明 PR 助理 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Reporting Brain。
【任務工作流】
1. 第一步：如果員工仲未揀 Scope_of_Word，請提醒佢喺對話框入面嘅清單直接勾選。
2. 第二步：一旦勾選完成，你就要根據佢揀咗嘅工作範疇（例如 Concept development 點樣諗出嚟），追問今次 Project 最難做嘅位 (Challenge) 同埋你哋嘅創新解決方案 (Solution)。
3. 不要客套，說話要快、準、直達重點。
"""

def log_event(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append(f"[{timestamp}] {level}: {msg}")

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "challenge": "", "solution": "", 
        "scope_of_word": [], "logo_white_b64": "", "logo_black_b64": "", "debug_logs": []
    }
    for field, default in fields.items():
        if field not in st.session_state: st.session_state[field] = default
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！今日個 Project 搞成點？請先喺下面勾選今次涉及邊幾項 Scope_of_Word（包括新加嘅 Concept development 💡），我再幫你執份報告！🥺"}]

def apply_neu_theme(gallery_files):
    track_text = ["client_name", "project_name", "challenge", "solution"]
    filled_text = sum(1 for f in track_text if str(st.session_state[f]).strip() != "")
    has_sow = 1 if st.session_state.scope_of_word else 0
    progress_percent = int(((filled_text + has_sow) / 5) * 100)
    st.markdown(f'<div style="text-align:right; color:#FF4B4B; font-weight:800; margin-bottom:10px;">PROGRESS: {progress_percent}%</div>', unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain 2.5", layout="wide")
    init_session_state()
    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)

    # 頂部上傳區 (適配手機)
    with st.expander("🖼️ 影像資產管理 (自動檢測像素)", expanded=True):
        gallery = st.file_uploader("拖放 8 張相片", accept_multiple_files=True, type=['jpg','png','jpeg'])

    apply_neu_theme(gallery)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Dashboard"])

    with tab1:
        col_chat, col_assets = st.columns([1.3, 1])
        with col_chat:
            st.markdown('<div class="neu-card" style="padding:20px; border-radius:20px; background:#E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff;">', unsafe_allow_html=True)
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            # --- 🚀 關鍵：在對話中嵌入 Checkbox (包含新選項) ---
            if not st.session_state.scope_of_word:
                st.info("請勾選今次涉及的工作範疇：")
                selected = st.multiselect("Select Scope_of_Word", SOW_OPTIONS, key="sow_widget")
                if st.button("確認勾選"):
                    st.session_state.scope_of_word = selected
                    st.session_state.messages.append({"role": "user", "content": f"我揀咗：{', '.join(selected)}"})
                    st.rerun()
            
            # 對話輸入
            if p := st.chat_input("話我知個 Project 嘅挑戰同解決方案..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION)
                        convo = f"User 已選 SOW: {st.session_state.scope_of_word}\n\n"
                        for m in st.session_state.messages: convo += f"{m['role']}: {m['content']}\n\n"
                        response = model.generate_content(convo)
                        st.write(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Admin Review")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        # Admin 頁面同步顯示新選項
        st.session_state.scope_of_word = st.multiselect("Scope_of_Word", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.session_state.challenge = st.text_area("The Hardest Part", st.session_state.challenge)
        st.session_state.solution = st.text_area("Our Innovation", st.session_state.solution)
        
        # Webhook URL (保持不變)
        WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyAjp74aiUDfsAyqwK_nDDu0q128ZL9az9yrC9201H6vYJ_gY8qI17962cLSWMexfiL/exec"
        
        if st.button("🚀 Confirm & Submit"):
            payload = {
                "project": st.session_state.project_name,
                "sow": ", ".join(st.session_state.scope_of_word),
                "challenge": st.session_state.challenge,
                "solution": st.session_state.solution
            }
            requests.post(WEBHOOK_URL, json=payload)
            st.balloons(); st.success("✅ 資料已同步，包括 Concept development！")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
