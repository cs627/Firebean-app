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

# --- 1. 配置 (更新為老細提供之最新 WEB URL) ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"

STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Lead Strategist. 
Identity: 'Institutional Cool'. Always output in Traditional Chinese (繁體中文).
Sync Rule: Output JSON with numbered keys (1_google_slide to 6_website) for API compatibility.
Include 'challenge_summary' and 'solution_summary' in your analysis.
"""

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
        response = model.generate_content(contents, generation_config={"response_mime_type": "application/json" if is_json else "text/plain", "temperature": 0.3})
        if response and response.text:
            raw = response.text.strip()
            if not is_json: return raw
            match = re.search(r'(\[.*\]|\{.*\})', raw, re.DOTALL)
            return match.group(1) if match else raw
    except Exception as e: log_debug(f"AI Error: {str(e)[:50]}", "error")
    return None

def create_dummy_data():
    """🚀 老細測試神器：生出 8 張相測試兩頁 Slide 填充"""
    st.session_state.client_name = "Firebean Dummy Test"
    st.session_state.project_name = "2026 Sync Full Test"
    st.session_state.venue = "HKCEC Hall 1"
    st.session_state.who_we_help = ["LIFESTYLE & CONSUMER"]
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope_of_word = ["Theme Design", "Concept Development", "Event Production"]
    st.session_state.open_question_ans = "AI Emotional Capture Strategy."
    
    # 生出 8 張 Dummy 相
    st.session_state.project_photos = []
    colors = [(255,0,0), (0,255,0), (0,0,255), (200,200,0), (200,0,200), (0,200,200), (100,100,100), (0,0,0)]
    for i, c in enumerate(colors):
        img = Image.new('RGB', (800, 600), color=c)
        d = ImageDraw.Draw(img); d.text((50,50), f"Dummy P{i+1}", fill=(255,255,255))
        buf = io.BytesIO(); img.save(buf, format="JPEG"); buf.seek(0)
        st.session_state.project_photos.append(buf)
    
    st.session_state.mc_questions = [{"id": 1, "question": "API Connection Test?", "options": ["OK", "FAIL"]}]
    st.session_state["ans_1"] = ["OK"]
    log_debug("🚀 一鍵填充 8 張相片數據完成！", "success")

def init_session_state():
    fields = {"active_tab": "📝 Project Collector", "client_name": "", "project_name": "", "venue": "", 
              "who_we_help": ["GOVERNMENT & PUBLIC SECTOR"], "what_we_do": [], "scope_of_word": [],
              "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
              "debug_logs": [], "mc_questions": [], "open_question_ans": "", "visual_facts": ""}
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def apply_styles():
    st.markdown("""<style>
        .stApp { background-color: #E0E5EC; color: #2D3436; }
        .neu-card { background: #E0E5EC; border-radius: 20px; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; padding: 25px; margin-bottom: 20px; }
        .mc-question { font-weight: 700; color: #FF0000; margin-top: 10px; border-left: 4px solid #FF0000; padding-left: 10px; }
        .debug-terminal { background: #1E1E1E; color: #00FF00; padding: 10px; font-size: 11px; border-radius: 10px; }
    </style>""", unsafe_allow_html=True)

# --- 4. Main ---
def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # Progress Calculation
    filled = sum([1 for f in ["client_name", "project_name", "venue"] if st.session_state[f]])
    percent = min(100, int((filled / 3) * 100))

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=150)
    with c2: st.metric("System Load", f"{percent}%")

    st.markdown("<br>", unsafe_allow_html=True)
    tabs = st.tabs(["📝 Project Collector", "📋 Review & Multi-Sync", "👥 CRM & Contacts"])

    with tabs[0]:
        if st.button("🧪 老細專用：一鍵填充 Dummy 測試數據 (含 8 張圖片)", use_container_width=True):
            create_dummy_data(); st.rerun()
        
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        st.session_state.client_name = col1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = col2.text_input("Project Name", st.session_state.project_name)
        st.session_state.venue = col3.text_input("Venue", st.session_state.venue)
        
        ca, cb, cc = st.columns(3)
        with ca: st.session_state.who_we_help = [st.radio("Category", WHO_WE_HELP_OPTIONS)]
        with cb: st.session_state.what_we_do = [opt for opt in WHAT_WE_DO_OPTIONS if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.what_we_do))]
        with cc: st.session_state.scope_of_word = [opt for opt in SOW_OPTIONS if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.scope_of_word))]
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("🪄 生成 20 條繁中 MC (Vision 分析)"):
            with st.spinner("Gemini 2.5 分析圖片中..."):
                st.session_state.visual_facts = call_gemini_sdk("Analyze event facts in Traditional Chinese.", image_files=st.session_state.project_photos)
                res = call_gemini_sdk(f"基於事實 {st.session_state.visual_facts} 生成 20 條繁中 MC。格式: [{{\"id\":1,\"question\":\"...\",\"options\":[\"A\",\"B\"]}}]", is_json=True)
                if res: st.session_state.mc_questions = json.loads(res)

        if st.session_state.mc_questions:
            for q in st.session_state.mc_questions:
                if isinstance(q, dict):
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                    st.session_state[f"ans_{q['id']}"] = [opt for opt in q['options'] if st.checkbox(opt, key=f"cb_{q['id']}_{opt}")]
        
        fup = st.file_uploader("Upload up to 8 Photos", accept_multiple_files=True)
        if fup: st.session_state.project_photos = fup
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        if st.button("🪄 生成文案及挑戰/方案"):
            with st.spinner("AI 構思中..."):
                sum_ans = [f"Q:{q['question']} A:{st.session_state.get(f'ans_{q.get('id')}')}" for q in st.session_state.mc_questions if isinstance(q, dict)]
                prompt = f"數據:{sum_ans}. Output JSON numbering keys 1_google_slide to 6_website. Plus 'challenge_summary' and 'solution_summary'."
                res = call_gemini_sdk(prompt, is_json=True)
                if res: st.session_state.ai_content = json.loads(res)

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync (Sheet + Slide + Folder)", type="primary", use_container_width=True):
                with st.spinner("正在執行多軌同步..."):
                    try:
                        sync_imgs = [base64.b64encode(f.read() if hasattr(f, 'read') else f.getvalue()).decode() for f in st.session_state.project_photos]
                        payload = {
                            "action": "sync_project", "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name, "venue": st.session_state.venue,
                            "category": st.session_state.who_we_help[0], "scope": ", ".join(st.session_state.scope_of_word),
                            "date": datetime.now().strftime("%Y-%m-%d"), 
                            "challenge": st.session_state.ai_content.get("challenge_summary", ""),
                            "solution": st.session_state.ai_content.get("solution_summary", ""),
                            "ai_content": st.session_state.ai_content, "images": sync_imgs
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sheet: {r1.status_code}, Slide: {r2.status_code}", "success")
                        st.balloons(); st.success("✅ 同步成功！")
                    except Exception as e: log_debug(f"Sync Fail: {str(e)}", "error")

    with st.expander("🛠️ Debug Terminal"):
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__": main()
