import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageEnhance, ImageOps, ImageDraw
from datetime import datetime

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

FIREBEAN_SYSTEM_PROMPT = "You are 'Firebean Brain', the Lead PR Strategist. Language: Traditional Chinese."

# --- 2. 核心邏輯 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key: return None
    try:
        genai.configure(api_key=secret_key)
        model = genai.GenerativeModel(model_name=STABLE_MODEL_ID, system_instruction=FIREBEAN_SYSTEM_PROMPT)
        contents = [prompt]
        if image_files:
            for f in image_files:
                img = Image.open(f)
                img.thumbnail((800, 800))
                contents.append(img)
        response = model.generate_content(contents, generation_config={"response_mime_type": "application/json" if is_json else "text/plain", "temperature": 0.2})
        if response and response.text:
            text = response.text.strip()
            if not is_json: return text
            match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
            return match.group(0) if match else text
    except Exception as e: log_debug(f"AI Error: {str(e)[:50]}", "warning")
    return None

def init_session_state():
    fields = {
        "active_tab": "📝 Project Collector",
        "client_name": "", "project_name": "", "venue": "", "youtube_link": "",
        "event_year": "2026", "event_month": "FEB",
        "who_we_help": [WHO_WE_HELP_OPTIONS[0]], "what_we_do": [], "scope_of_work": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", 
        "challenge": "", "solution": "", "visual_facts": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def fill_dummy_data():
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = "2026 旗艦同步測試"
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.youtube_link = "https://youtube.com/firebean_demo_2026"
    st.session_state.who_we_help = ["LIFESTYLE & CONSUMER"]
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope_of_work = ["Theme Design", "Event Production", "Concept Development"]
    st.session_state.open_question_ans = "將20個通用診斷問題及其抽象答案,轉化為一套連貫、引人入勝且可操作的跨平台策略。"
    
    # 生 8 張彩色圖片
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    
    # 20 題 MC
    st.session_state.mc_questions = [{"id": i+1, "question": f"指標 {i+1}？", "options": ["優化", "維持"]} for i in range(20)]
    for i in range(1, 21): st.session_state[f"ans_{i}"] = ["優化"]
    
    dummy_logo = base64.b64encode(create_dummy_image("#FFFFFF", "LOGO").getvalue()).decode()
    st.session_state.logo_black = dummy_logo
    st.session_state.logo_white = dummy_logo

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    d = ImageDraw.Draw(img); d.text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO(); img.save(buf, format="JPEG"); buf.seek(0)
    return buf

# --- 3. Main ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()

    # 進度計算 (11 維度)
    score_items = ["client_name", "project_name", "venue", "youtube_link", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.who_we_help else 0)
    filled += (1 if st.session_state.what_we_do else 0)
    filled += (1 if st.session_state.scope_of_work else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    mc_done = sum([1 for i in range(1, 21) if st.session_state.get(f"ans_{i}")])
    filled += (1 if mc_done == 20 else 0)
    percent = min(100, int((filled / 11) * 100))

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=160)
    with c2: st.metric("Progress", f"{percent}%")

    if percent == 100 and st.session_state.active_tab == "📝 Project Collector":
        st.session_state.active_tab = "📋 Review & Multi-Sync"; st.rerun()

    st.markdown("---")
    tab_list = ["📝 Project Collector", "📋 Review & Multi-Sync", "🛠️ Debug"]
    nav_cols = st.columns(3)
    for i, t in enumerate(tab_list):
        if nav_cols[i].button(t, use_container_width=True, type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t; st.rerun()

    if st.session_state.active_tab == "📝 Project Collector":
        if st.button("🧪 老細一鍵填充測試", use_container_width=True): fill_dummy_data(); st.rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Black Logo", type=['png'], key="l_b")
            if ub: st.session_state.logo_black = base64.b64encode(ub.read()).decode()
        with col2:
            uw = st.file_uploader("White Logo", type=['png'], key="l_w")
            if uw: st.session_state.logo_white = base64.b64encode(uw.read()).decode()

        b1, b2, b3, b4 = st.columns(4)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b4.text_input("YouTube", st.session_state.youtube_link)

        ca, cb, cc = st.columns(3)
        with ca: st.session_state.who_we_help = [st.radio("Who we help", WHO_WE_HELP_OPTIONS)]
        with cb: st.session_state.what_we_do = [o for o in WHAT_WE_DO_OPTIONS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.what_we_do))]
        with cc: st.session_state.scope_of_work = [o for o in SOW_OPTIONS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.scope_of_work))]
        
        fup = st.file_uploader("Photos", accept_multiple_files=True)
        if fup: st.session_state.project_photos = fup

    elif st.session_state.active_tab == "📋 Review & Multi-Sync":
        if st.button("🪄 生成策略文案"):
            res = call_gemini_sdk("Generate JSON strategy.", is_json=True)
            if res:
                data = json.loads(res)
                st.session_state.ai_content = data
                st.session_state.challenge = data.get("challenge_summary", "")
                st.session_state.solution = data.get("solution_summary", "")

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync", type="primary", use_container_width=True):
                with st.spinner("🔄 同步中..."):
                    try:
                        imgs = [base64.b64encode(f.read() if hasattr(f, "read") else f.getvalue()).decode() for f in st.session_state.project_photos]
                        # 🚀 校準對位 Payload
                        payload = {
                            "action": "sync_project",
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue,
                            "date": f"{st.session_state.event_year} {st.session_state.event_month}",
                            "youtube": st.session_state.youtube_link,
                            "category": st.session_state.who_we_help[0], # 修正：Key 改為 category
                            "category_what": ", ".join(st.session_state.what_we_do),
                            "scope": ", ".join(st.session_state.scope_of_work),
                            "challenge": st.session_state.challenge,
                            "solution": st.session_state.solution,
                            "logo_white": st.session_state.logo_white,
                            "logo_black": st.session_state.logo_black,
                            "images": imgs,
                            "ai_content": st.session_state.ai_content
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        st.balloons(); st.success("✅ 同步對位成功！")
                    except Exception as e: st.error(f"Sync Fail: {str(e)}")

    elif st.session_state.active_tab == "🛠️ Debug":
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(logs, unsafe_allow_html=True)

if __name__ == "__main__": main()
