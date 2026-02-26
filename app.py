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

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
Motto: 'Turn Policy into Play'.
"""

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
            if response.text:
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
        "active_tab": "📝 Project Collector", # 新增：控制目前所在的 Tab
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "who_we_help": [WHO_WE_HELP_OPTIONS[0]], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": [],
        "mc_questions": [], "open_question_ans": "", "challenge": "", "solution": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 120px; height: 120px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="120" height="120"><circle stroke="#d1d9e6" stroke-width="8" fill="transparent" r="50" cx="60" cy="60"/><circle stroke="#FF0000" stroke-width="8" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="50" cx="60" cy="60" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg>
            <div style="position: absolute; font-size: 22px; font-weight: 900; color: #2D3436;">{percent}%</div>
        </div>
    </div>
    """

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; }
        .neu-card { background: #E0E5EC; border-radius: 20px; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; padding: 25px; margin-bottom: 20px; color: #2D3436; }
        h1, h2, h3, label, p { color: #2D3436 !important; font-weight: 700 !important; }
        input, textarea, div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #2D3436 !important; }
        .hero-border { border: 4px solid #FF0000; border-radius: 12px; }
        .ai-status-tag { background: #FF3333; color: white !important; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 800; display: inline-block; margin-bottom: 5px; }
        .mc-question { font-weight: 600; color: #d32f2f !important; margin-top: 15px; }
        
        /* 自定義全闊度 Tab 按鈕樣式 */
        .nav-btn {
            width: 100%;
            border-radius: 15px;
            padding: 15px;
            text-align: center;
            font-weight: 800;
            cursor: pointer;
            border: none;
            margin-bottom: 10px;
            transition: 0.3s;
        }
        .active-nav {
            background: #FF0000;
            color: white !important;
            box-shadow: inset 4px 4px 8px #880000, inset -4px -4px 8px #ff4444;
        }
        .inactive-nav {
            background: #E0E5EC;
            color: #2D3436 !important;
            box-shadow: 6px 6px 12px #bec3c9, -6px -6px 12px #ffffff;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 3. Main UI ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # Progress 計算 (10 維度)
    score_items = ["client_name", "project_name", "venue", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    filled += (1 if len(st.session_state.mc_questions) == 20 else 0)
    percent = int((filled / 10) * 100)
    if percent > 100: percent = 100

    # Header 佈局
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    # --- 自定義顯眼導航欄 (取代 st.tabs) ---
    st.markdown("<br>", unsafe_allow_html=True)
    nav_cols = st.columns(3)
    tab_list = ["📝 Project Collector", "📋 Review & Multi-Sync", "👥 CRM & Contacts"]
    
    for i, tab_name in enumerate(tab_list):
        is_active = st.session_state.active_tab == tab_name
        btn_type = "primary" if is_active else "secondary"
        # 為了模擬 Tab 按鈕，我們直接使用 Streamlit Button 並透過 CSS 修改外觀 (或者直接用 st.button 並靠 CSS)
        if nav_cols[i].button(tab_name, use_container_width=True, key=f"nav_{i}", type=btn_type):
            st.session_state.active_tab = tab_name
            st.rerun()

    st.markdown("---")

    # --- 分頁內容切換 ---
    
    # --- TAB 1: PROJECT COLLECTOR ---
    if st.session_state.active_tab == "📝 Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Assets & Core Info")
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Upload Black Logo", type=['png'], key="logo_b_up")
            if ub and st.button("Fix Black"): st.session_state.logo_black = standardize_logo(ub)
        with col2:
            uw = st.file_uploader("Upload White Logo", type=['png'], key="logo_w_up")
            if uw and st.button("Fix White"): st.session_state.logo_white = standardize_logo(uw)
        
        b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b4.text_input("YouTube Link (Optional)", st.session_state.youtube_link)
        
        c_a, c_b, c_c = st.columns(3)
        with c_a: 
            st.markdown("**👥 Category**")
            st.session_state.who_we_help = [st.radio("Category", WHO_WE_HELP_OPTIONS, label_visibility="collapsed")]
        with c_b: 
            st.markdown("**🚀 What we do**")
            st.session_state.what_we_do = [opt for opt in WHAT_WE_DO_OPTIONS if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.what_we_do))]
        with c_c:
            st.markdown("**🛠️ Scope**")
            st.session_state.scope_of_word = [opt for opt in SOW_OPTIONS if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.scope_of_word))]
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🧠 20 MC Soul Extraction")
            if st.button("🪄 生成 20 條 MC 題目 (繁體中文)"):
                prompt = f"Generate 20 MC questions for project: {st.session_state.project_name} in Traditional Chinese..."
                res = call_gemini_sdk(prompt)
                if res: st.session_state.mc_questions = json.loads(res)
            
            if st.session_state.mc_questions:
                for q in st.session_state.mc_questions:
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                    st.session_state[f"ans_{q['id']}"] = st.multiselect("Options", q['options'], key=f"q_{q['id']}")
                st.session_state.open_question_ans = st.text_area("覺得我哋嘅概念最特別是什麼？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Require 4+ Photos)")
            files = st.file_uploader("Upload up to 8 Photos", accept_multiple_files=True, key="photo_up")
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

        # 🚀 關鍵邏輯：當進度達 100% 時顯示跳轉按鈕
        if percent == 100:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 資料已齊全！進入 Review & Multi-Sync", use_container_width=True, type="primary"):
                st.session_state.active_tab = "📋 Review & Multi-Sync"
                st.rerun()

    # --- TAB 2: REVIEW & SYNC ---
    elif st.session_state.active_tab == "📋 Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Platform Sync")
        if st.button("🪄 一鍵生成所有平台文案 (Follow DNA)"):
            if not st.session_state.logo_white and not st.session_state.logo_black:
                st.error("🚨 阻截：請先回到第一頁上傳 Logo")
            elif len(st.session_state.project_photos) < 4:
                st.error("🚨 阻截：請至少上傳 4 張相片")
            else:
                # 確保 IG 文案嚴格遵守 150 字及繁體中文規則
                prompt = f"Analyze project {st.session_state.project_name}... Generate JSON for 6 platforms. IMPORTANT: Instagram content must be Traditional Chinese and under 150 words."
                res = call_gemini_sdk(prompt)
                if res:
                    st.session_state.ai_content = json.loads(res)
                    st.success("✅ 文案已完美生成！")
        
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
                    st.balloons(); st.success("✅ Master DB & Google Drive 同步成功！")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 3: CRM & CONTACTS ---
    elif st.session_state.active_tab == "👥 CRM & Contacts":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("👥 CRM 聯絡人管理")
        col_em, col_name = st.columns(2)
        with col_em: new_email = st.text_input("Customer Email", key="crm_email")
        with col_name: new_name = st.text_input("Customer Name (Optional)", key="crm_name")
        
        if st.button("📥 手動新增至 CRM 名單"):
            if "@" in new_email:
                contact_payload = {"action": "add_contact", "email": new_email, "name": new_name}
                res = requests.post(SHEET_SCRIPT_URL, json=contact_payload)
                if res.status_code == 200: st.success(f"✅ {new_email} 已成功加入獨立的 Contacts 工作表！")
            else: st.error("請輸入有效的電郵。")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
