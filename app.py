import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import requests
from PIL import Image, ImageEnhance, ImageOps
from datetime import datetime

# --- 1. 核心配置與 Webhook URL ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycb6YNAjNNndamdkcULS71Q_qkkbclBViLlx9B8e7LaaxyapMc7jsgdvhMHZ3d_wLzXw/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbya_pl6h99zY_LrURojCL86c20NwxdeW6V9bhCXqgPjJdz2NVPgeFThthcR6gfw0d1P/exec"

API_KEYS_POOL = [
    "AIzaSyA-5qXWjtzlUWP0IDMVUByMXdbylt8rTSA",
    "AIzaSyCVuoSuWV3tfGCu2tjikCkMOVRWCBFne20",
    "AIzaSyCZKtjLqN4FUQ76c3DYoDW20tTkFki_Rxk"
]

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 2. 核心邏輯 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    all_keys = ([secret_key] if secret_key else []) + API_KEYS_POOL
    for key in all_keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content([prompt] + ([image_file] if image_file else []))
            if response and response.text:
                cleaned = response.text.strip().replace("```json", "").replace("```", "")
                return cleaned
        except: continue
    return None

def standardize_logo(logo_file):
    try:
        raw = Image.open(logo_file)
        img = ImageOps.exif_transpose(raw).convert("RGBA")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

def manna_ai_enhance(image_file):
    try:
        raw_img = Image.open(image_file)
        img = ImageOps.exif_transpose(raw_img).convert("RGB")
        return ImageEnhance.Contrast(img).enhance(1.15)
    except: return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "who_we_help": [WHO_WE_HELP_OPTIONS[0]], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": [],
        "mc_questions": [], "open_question_ans": "", "challenge": "", "solution": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def apply_styles():
    st.markdown("""
        <style>
        .stApp { background-color: #E0E5EC; color: #2D3436; }
        .neu-card { background: #E0E5EC; border-radius: 20px; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; padding: 25px; margin-bottom: 20px; color: #2D3436; }
        h1, h2, h3, label, p { color: #2D3436 !important; }
        input, textarea, div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #2D3436 !important; }
        </style>
    """, unsafe_allow_html=True)

# --- 3. Main UI ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.write("### 🚀 PR Architect Control Panel")

    tab1, tab2, tab3 = st.tabs(["📝 Project Collector", "📋 Review & Multi-Sync", "👥 CRM & Contacts"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Assets & Core Info")
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Upload Black Logo", type=['png'], key="logo_b_up")
            if ub and st.button("Fix Black"): st.session_state.logo_black = standardize_logo(ub)
        with col2:
            uw = st.file_uploader("Upload White Logo", type=['png'], key="logo_w_up")
            if uw and st.button("Fix White"): st.session_state.logo_white = standardize_logo(uw)
        
        st.session_state.client_name = st.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = st.text_input("Project", st.session_state.project_name)
        st.session_state.venue = st.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = st.text_input("YouTube Link (Optional)", st.session_state.youtube_link)
        
        c_a, c_b, c_c = st.columns(3)
        with c_a: st.session_state.who_we_help = [st.radio("Category", WHO_WE_HELP_OPTIONS)]
        with c_b: 
            st.markdown("**What we do**")
            st.session_state.what_we_do = [opt for opt in WHAT_WE_DO_OPTIONS if st.checkbox(opt, key=f"w_{opt}")]
        with c_c:
            st.markdown("**Scope**")
            st.session_state.scope_of_word = [opt for opt in SOW_OPTIONS if st.checkbox(opt, key=f"s_{opt}")]
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📸 Gallery")
        files = st.file_uploader("Upload Photos (min 4)", accept_multiple_files=True, key="photo_up")
        if files:
            st.session_state.project_photos = files
            hero_choice = st.radio("🌟 Select Hero Banner", [f"P{i+1}" for i in range(len(files))], horizontal=True)
            st.session_state.hero_index = int(hero_choice[1:]) - 1
            cols = st.columns(4)
            for i, f in enumerate(files):
                with cols[i%4]:
                    img = manna_ai_enhance(f)
                    st.image(img, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🧠 20 MC Soul Extraction")
        if st.button("🪄 Generate 20 MCs"):
            prompt = f"Generate 20 MC questions for project: {st.session_state.project_name} in Traditional Chinese..."
            res = call_gemini_sdk(prompt, is_json=True)
            if res: st.session_state.mc_questions = json.loads(res)
        
        if st.session_state.mc_questions:
            for q in st.session_state.mc_questions:
                st.write(f"**Q: {q['question']}**")
                st.multiselect("Select options", q['options'], key=f"ans_{q['id']}")
            st.session_state.open_question_ans = st.text_area("What makes this concept special?", st.session_state.open_question_ans)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Platform Sync")
        if st.button("🪄 一鍵生成所有平台文案 (Follow DNA)"):
            prompt = f"Analyze project {st.session_state.project_name} and generate JSON for 6 platforms (LinkedIn, FB, Threads, IG, Web)..."
            res = call_gemini_sdk(prompt, is_json=True)
            if res:
                st.session_state.ai_content = json.loads(res)
                st.session_state.challenge = st.session_state.ai_content.get("challenge_summary", "")
                st.session_state.solution = st.session_state.ai_content.get("solution_summary", "")
                st.success("✅ 文案已生成！")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync (Sheet + Slide + Drive)"):
                with st.spinner("🔄 多軌同步中..."):
                    payload = {
                        "action": "sync_project",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "client_name": st.session_state.client_name,
                        "project_name": st.session_state.project_name,
                        "event_date": f"{st.session_state.event_year} {st.session_state.event_month}",
                        "venue": st.session_state.venue,
                        "youtube_link": st.session_state.youtube_link,
                        "category_who": ", ".join(st.session_state.who_we_help),
                        "category_what": ", ".join(st.session_state.what_we_do),
                        "scope_of_work": ", ".join(st.session_state.scope_of_word),
                        "challenge": st.session_state.challenge,
                        "solution": st.session_state.solution,
                        "open_question": st.session_state.open_question_ans,
                        "ai_content": st.session_state.ai_content,
                        "logo_black": st.session_state.logo_black,
                        "logo_white": st.session_state.logo_white,
                        "images": [base64.b64encode(f.getvalue()).decode() for f in st.session_state.project_photos]
                    }
                    requests.post(SHEET_SCRIPT_URL, json=payload)
                    requests.post(SLIDE_SCRIPT_URL, json=payload)
                    st.balloons(); st.success("✅ Master DB 同步成功！")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("👥 CRM 聯絡人管理")
        col_em, col_name = st.columns(2)
        with col_em: new_email = st.text_input("Customer Email", key="crm_email")
        with col_name: new_name = st.text_input("Customer Name (Optional)", key="crm_name")
        
        if st.button("📥 手動新增至 CRM 名單"):
            if "@" in new_email:
                contact_payload = {"action": "add_contact", "email": new_email, "name": new_name}
                res = requests.post(SHEET_SCRIPT_URL, json=contact_payload)
                if res.status_code == 200: st.success(f"✅ {new_email} 已成功加入 Contacts 工作表！")
            else: st.error("請輸入有效的電郵。")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
