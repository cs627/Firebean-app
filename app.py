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

# --- 1. 核心性格：極速報告員 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Reporting Assistant。幫老細收集「活動報告」最精華嘅料。
【追問方針】
1. **唔好廢話**：直接問重點。
2. **直擊痛點**：問「Project 邊度最難做？」。
3. **客戶期望**：問「客戶最後最想達到咩效果？」。
4. **遊戲創新**：問你哋改咗咩遊戲規則令到多人玩？
每次回覆最後，必須另起一行輸出 JSON：
[DATA:{"client_name":"","project_name":"","venue":"","challenge":"","solution":""}]
"""

# --- 2. 初始化與視覺 ---
def init_session_state():
    fields = ["client_name", "project_name", "venue", "challenge", "solution", "logo_b64", "debug_logs"]
    for field in fields:
        if field not in st.session_state: st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細，我已經入咗 2.5 大腦！今日個 Project 邊度最棘手？你哋點改遊戲玩法架？🥺"}]
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []

def apply_neu_theme():
    track_fields = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled = sum(1 for f in track_fields if str(st.session_state[f]).strip() != "")
    progress_percent = int((filled / len(track_fields)) * 100)
    st.markdown(f"""
        <style>
        header {{visibility: hidden;}} footer {{visibility: hidden;}}
        .stApp {{ background-color: #E0E5EC; color: #2D3436; }}
        .energy-bar-bg {{ height: 12px; background: #E0E5EC; border-radius: 10px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; overflow: hidden; margin-top:10px; }}
        .energy-bar-fill {{ height: 100%; width: {progress_percent}%; background: linear-gradient(90deg, #FF4B4B, #FF8080); transition: width 0.8s; }}
        .neu-card {{ background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 20px; margin-bottom: 20px; }}
        </style>
        <div class="energy-bar-bg"><div class="energy-bar-fill"></div></div>
        <div style="font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-top:5px;">REPORT COMPLETION: {progress_percent}%</div>
    """, unsafe_allow_html=True)

def get_base64_image(file):
    try: return base64.b64encode(file.getvalue()).decode()
    except: return ""

def main():
    st.set_page_config(page_title="Firebean Brain Center", layout="wide")
    init_session_state()
    apply_neu_theme()

    # --- API 安全讀取 ---
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key: st.error("⚠️ 未偵測到 API Key。"); return
    genai.configure(api_key=api_key)

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)

    tab1, tab2 = st.tabs(["💬 Data Collector", "⚙️ Admin Dashboard"])

    with tab1:
        col_l, col_r = st.columns([1.3, 1])
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if p := st.chat_input("輸入活動細節..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    with st.spinner("分析中..."):
                        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION)
                        convo = ""
                        for m in st.session_state.messages: convo += f"{m['role']}: {m['content']}\n\n"
                        response = model.generate_content(convo)
                        # 自動提取 JSON
                        match = re.search(r"\[DATA:(\{.*?\})\]", response.text)
                        if match:
                            extracted = json.loads(match.group(1))
                            for k, v in extracted.items():
                                if v and not st.session_state.get(k): st.session_state[k] = v
                        clean_text = re.sub(r"\[DATA:\{.*?\}\]", "", response.text).strip()
                        st.write(clean_text)
                        st.session_state.messages.append({"role": "assistant", "content": clean_text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("去背 Logo", type=['png','jpg','jpeg'], key="l_up")
            if logo_f and st.button("🪄 轉化白色"):
                with st.spinner("處理中..."):
                    img = Image.open(logo_f)
                    out = remove(img)
                    final = Image.composite(Image.new('RGBA', out.size, (255,255,255,255)), Image.new('RGBA', out.size, (0,0,0,0)), out.getchannel('A'))
                    st.image(final, width=120)
                    buf = io.BytesIO(); final.save(buf, format="PNG")
                    st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 8 Photos Grid")
            gallery = st.file_uploader("上傳 8 張相", accept_multiple_files=True, type=['jpg','png','jpeg'])
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("⚙️ Final Preview")
        st.session_state.project_name = st.text_input("Project", st.session_state.project_name)
        st.session_state.client_name = st.text_input("Client", st.session_state.client_name)
        st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        st.session_state.challenge = st.text_area("Hardest Part", st.session_state.challenge)
        st.session_state.solution = st.text_area("Innovation", st.session_state.solution)
        
        # 🔗 請貼上你剛才獲得的 GAS Webhook URL
        WEBHOOK_URL = "https://script.google.com/macros/s/你的GAS腳本ID/exec" 
        
        if st.button("🚀 Confirm & Submit to Cloud"):
            with st.spinner("正在同步..."):
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
                        st.balloons(); st.success("✅ 同步成功！細 Folder 已生成。")
                    else: st.error(f"連線失敗 (Code: {res.status_code})")
                except Exception as e: st.error(f"Error: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
