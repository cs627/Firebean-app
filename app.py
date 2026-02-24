import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import json
import re
from PIL import Image
from rembg import remove

# --- 1. 定義 Firebean 常見 Scope_of_Word 選項 ---
SOW_OPTIONS = [
    "Overall planning and coordination",
    "Event Production / Theme Development",
    "Social Media Management",
    "KOL 網紅",
    "Media Pitching",
    "Interactive Game preparation",
    "Theme design"
]

# --- 2. 核心性格：Scope_of_Word 引導型核數師 ---
SYSTEM_INSTRUCTION = f"""
你係 Firebean Reporting Brain。任務係幫老細收集資料。
【反問規則：Scope_of_Word】
1. 針對項目：{", ".join(SOW_OPTIONS)}。
2. 你要用「反問形式」讓員工直接答「是/否」，從而快速勾選。
3. 語氣快脆，唔好客套。
【隱形同步標籤】
每次回覆最後輸出 JSON，確保 Key 是 scope_of_word：
[DATA:{{"client_name":"","project_name":"","venue":"","challenge":"","solution":"","scope_of_word":[]}}]
"""

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "challenge": "", "solution": "", 
        "scope_of_word": [], "logo_white_b64": "", "logo_black_b64": "", "debug_logs": []
    }
    for field, default in fields.items():
        if field not in st.session_state: st.session_state[field] = default
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！我準備好執報告。今次 Project 有無做 Overall planning and coordination？🥺"}]

def apply_neu_theme(gallery_files):
    track_text = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled_text = sum(1 for f in track_text if str(st.session_state[f]).strip() != "")
    # 進度計算包括 Scope_of_Word
    has_sow = 1 if st.session_state.scope_of_word else 0
    progress_percent = int(((filled_text + (1 if gallery_files else 0) + has_sow) / 7) * 100)
    st.markdown(f'<div style="text-align:right; color:#FF4B4B; font-weight:800;">REPORT READY: {progress_percent}%</div>', unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain 2.5", layout="wide")
    init_session_state()
    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)

    gallery = st.sidebar.file_uploader("📸 拖放相片", accept_multiple_files=True, type=['jpg','png','jpeg'])
    apply_neu_theme(gallery)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Dashboard"])

    with tab1:
        # Chatbot 區域 (AI 會根據 SYSTEM_INSTRUCTION 自動反問)
        col_chat, col_assets = st.columns([1.3, 1])
        with col_chat:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if p := st.chat_input("答 AI 問題 (有/無)..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    with st.spinner("整理中..."):
                        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION)
                        convo = "".join([f"{m['role']}: {m['content']}\n\n" for m in st.session_state.messages])
                        response = model.generate_content(convo)
                        
                        # 自動提取 DATA
                        match = re.search(r"\[DATA:(.*?)\]", response.text, re.DOTALL)
                        if match:
                            try:
                                data = json.loads(match.group(1))
                                if data.get("client_name"): st.session_state.client_name = data["client_name"]
                                if data.get("scope_of_word"): 
                                    st.session_state.scope_of_word = list(set(st.session_state.scope_of_word + data["scope_of_word"]))
                            except: pass
                        
                        clean_text = re.sub(r"\[DATA:.*?\]", "", response.text, flags=re.DOTALL).strip()
                        st.write(clean_text)
                        st.session_state.messages.append({"role": "assistant", "content": clean_text})
                st.rerun()

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Admin Review")
        
        # --- 這裡是 Scope_of_Word 的自動/手動勾選區 ---
        st.subheader("🛠️ Scope_of_Word (AI 自動識別項目)")
        st.session_state.scope_of_word = st.multiselect("已確認服務", SOW_OPTIONS, default=st.session_state.scope_of_word)
        
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.challenge = st.text_area("The Hardest Part", st.session_state.challenge)
        st.session_state.solution = st.text_area("Our Innovation", st.session_state.solution)
        
        # Webhook URL
        WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyAjp74aiUDfsAyqwK_nDDu0q128ZL9az9yrC9201H6vYJ_gY8qI17962cLSWMexfiL/exec"
        
        if st.button("🚀 Confirm & Submit to Master DB"):
            try:
                payload = {
                    "project": st.session_state.project_name,
                    "client": st.session_state.client_name,
                    "scope_of_word": ", ".join(st.session_state.scope_of_word), # 打包成字串傳送
                    "challenge": st.session_state.challenge,
                    "solution": st.session_state.solution,
                }
                requests.post(WEBHOOK_URL, json=payload)
                st.balloons(); st.success("✅ 同步成功！資料已寫入 Scope_of_Word Column。")
            except Exception as e: st.error(f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
