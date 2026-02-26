import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageEnhance, ImageOps
from datetime import datetime

# --- 1. 核心配置與 Webhook URL (確保與你的 App Script 吻合) ---
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
Professional English for Slides/LinkedIn. Canto-slang for IG/Threads. Trilingual for Website.
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
    model_name = "gemini-2.5-flash"

    for idx, key in enumerate(all_keys):
        try:
            is_secret = "(Secret Key)" if (secret_key and idx == 0) else f"(Pool Key #{idx})"
            log_debug(f"Attempting API with Key {is_secret}...", "info")
            genai.configure(api_key=key)
            config = genai.types.GenerationConfig(response_mime_type="application/json" if is_json else "text/plain")
            model = genai.GenerativeModel(model_name=model_name, system_instruction=FIREBEAN_SYSTEM_PROMPT)
            
            contents = [prompt]
            if image_file: contents.append(image_file)
            response = model.generate_content(contents, generation_config=config)
            
            if response and response.text:
                log_debug(f"✅ Success with Key {is_secret}!", "success")
                raw_text = response.text.strip()
                if not is_json: return raw_text
                # JSON 提取防爆
                json_match = re.search(r'(\[.*\]|\{.*\})', raw_text, re.DOTALL)
                return json_match.group(1) if json_match else raw_text
        except Exception as e:
            log_debug(f"Key Error {is_secret}: {str(e)}", "warning")
            continue
    return None

def test_api_connection():
    log_debug("🚀 Starting SDK Connection Test...", "info")
    res = call_gemini_sdk("Ping test. Respond exactly: 'Firebean 2.5 Online.'")
    if res: st.toast("✅ SDK 連線成功！")
    else: st.toast("❌ 連線失敗")

def standardize_logo(logo_file):
    try:
        raw = Image.open(logo_file)
        img = ImageOps.exif_transpose(raw).convert("RGBA")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        log_debug(f"Logo '{logo_file.name}' encoded to Base64 PNG.", "success")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log_debug(f"Logo Fix Error: {str(e)}", "error")
        return ""

def manna_ai_enhance(image_file):
    try:
        raw_img = Image.open(image_file)
        img = ImageOps.exif_transpose(raw_img).convert("RGB")
        return ImageEnhance.Contrast(img).enhance(1.15)
    except: return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

def init_session_state():
    fields = {
        "active_tab": "📝 Project Collector",
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "who_we_help": [WHO_WE_HELP_OPTIONS[0]], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": [],
        "mc_questions": [], "open_question_ans": "", "challenge": "", "solution": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# --- 3. UI 樣式 ---

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 110px; height: 110px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="110" height="110"><circle stroke="#d1d9e6" stroke-width="8" fill="transparent" r="45" cx="55" cy="55"/><circle stroke="#FF0000" stroke-width="8" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="45" cx="55" cy="55" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg>
            <div style="position: absolute; font-size: 20px; font-weight: 900; color: #2D3436;">{percent}%</div>
        </div>
    </div>
    """

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 20px; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; padding: 25px; margin-bottom: 20px; color: #2D3436; }
        h1, h2, h3, label, p { color: #2D3436 !important; font-weight: 700 !important; }
        input, textarea, div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #2D3436 !important; }
        .mc-question { font-weight: 600; color: #d32f2f !important; margin-top: 15px; }
        .mc-container { margin-bottom: 15px; padding-left: 10px; border-left: 3px solid #FF0000; }
        .debug-terminal { background: #1E1E1E !important; color: #00FF00 !important; padding: 12px; font-family: 'Courier New', monospace; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px 10px 0 0; max-height: 250px; overflow-y: auto; margin-top: 30px; }
        .debug-success { color: #00FF00 !important; font-weight: bold; }
        .debug-error { color: #FF5555 !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Main App ---

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

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    # 全闊度顯眼導航
    nav_cols = st.columns(3)
    tab_list = ["📝 Project Collector", "📋 Review & Multi-Sync", "👥 CRM & Contacts"]
    for i, t in enumerate(tab_list):
        if nav_cols[i].button(t, use_container_width=True, key=f"nav_{i}", type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t
            st.rerun()
    st.markdown("---")

    # --- TAB 1: COLLECTOR ---
    if st.session_state.active_tab == "📝 Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Assets & Core Info")
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Upload Black Logo", type=['png'], key="logo_b")
            if ub and st.button("Fix Black"): st.session_state.logo_black = standardize_logo(ub)
        with col2:
            uw = st.file_uploader("Upload White Logo", type=['png'], key="logo_w")
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
            new_wwd = []
            for opt in WHAT_WE_DO_OPTIONS:
                if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.what_we_do)): new_wwd.append(opt)
            st.session_state.what_we_do = new_wwd
        with c_c:
            st.markdown("**🛠️ Scope**")
            new_sow = []
            for opt in SOW_OPTIONS:
                if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.scope_of_word)): new_sow.append(opt)
            st.session_state.scope_of_word = new_sow
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🧠 專案靈魂萃取器 (20 MC Checkbox)")
            if st.button("🪄 生成 20 條 MC 題目"):
                with st.spinner("AI 正在根據 DNA 分析出題..."):
                    prompt = f"Generate exactly 20 MC questions for project: {st.session_state.project_name} in Traditional Chinese. Output strictly as JSON array of objects: [{{'id': 1, 'question': '...', 'options': ['A...', 'B...', 'C...', 'D...']}}]"
                    res = call_gemini_sdk(prompt, is_json=True)
                    if res:
                        try:
                            st.session_state.mc_questions = json.loads(res)
                            st.success("✅ 題目已生成！")
                        except: st.error("JSON 格式出錯，請重試。")
            
            if st.session_state.mc_questions:
                for i, q in enumerate(st.session_state.mc_questions):
                    q_id = q.get('id', i + 1)
                    st.markdown(f"<div class='mc-question'>Q{q_id}. {q.get('question')}</div>", unsafe_allow_html=True)
                    st.markdown("<div class='mc-container'>", unsafe_allow_html=True)
                    selected = []
                    for opt_idx, opt_text in enumerate(q.get('options', [])):
                        if st.checkbox(opt_text, key=f"mc_cb_{q_id}_{opt_idx}"): selected.append(opt_text)
                    st.session_state[f"ans_{q_id}"] = selected
                    st.markdown("</div>", unsafe_allow_html=True)
                st.session_state.open_question_ans = st.text_area("覺得我哋嘅概念最特別是什麼？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Require 4+)")
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

        if percent == 100:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 資料已齊全！進入 Review & Multi-Sync", use_container_width=True, type="primary"):
                st.session_state.active_tab = "📋 Review & Multi-Sync"
                st.rerun()

    # --- TAB 2: REVIEW & SYNC ---
    elif st.session_state.active_tab == "📋 Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Platform Sync")
        if st.button("🪄 一鍵生成六大平台文案"):
            with st.spinner("AI 根據 PDF 指引生成中 (IG 字數及語言限制中)..."):
                prompt = f"Analyze project {st.session_state.project_name}... Generate JSON for 6 platforms. IG must be Traditional Chinese and <150 words."
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    try:
                        st.session_state.ai_content = json.loads(res)
                        st.session_state.challenge = st.session_state.ai_content.get("challenge_summary", "")
                        st.session_state.solution = st.session_state.ai_content.get("solution_summary", "")
                        st.success("✅ 文案已完美生成！")
                    except: st.error("文案 JSON 格式出錯")
        
        if st.session_state.ai_content:
            st.subheader("✨ AI 生成預覽")
            st.json(st.session_state.ai_content)
            if st.button("🔥 Confirm & Sync (Sheet + Slide + Drive)", use_container_width=True, type="primary"):
                with st.spinner("🔄 多軌同步中..."):
                    try:
                        # 匯總 MC 答案
                        sum_ans = []
                        if st.session_state.mc_questions:
                            for i, q in enumerate(st.session_state.mc_questions):
                                q_id = q.get('id', i+1)
                                ans = st.session_state.get(f"ans_{q_id}", [])
                                sum_ans.append(f"Q: {q.get('question')} | A: {', '.join(ans)}")
                        
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
                            "mc_summary": "\n".join(sum_ans),
                            "ai_content": st.session_state.ai_content,
                            "logo_black": st.session_state.logo_black,
                            "logo_white": st.session_state.logo_white,
                            "images": [base64.b64encode(f.getvalue()).decode() for f in st.session_state.project_photos]
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sheet: {r1.status_code}, Slide: {r2.status_code}", "success")
                        st.balloons(); st.success("✅ Master DB & Google Slide 同步成功！")
                    except Exception as e: log_debug(f"Sync Error: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 3: CRM ---
    elif st.session_state.active_tab == "👥 CRM & Contacts":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("👥 CRM 聯絡人管理")
        col_em, col_name = st.columns(2)
        with col_em: new_email = st.text_input("Customer Email", key="crm_em")
        with col_name: new_name = st.text_input("Customer Name", key="crm_na")
        if st.button("📥 手動新增至 CRM"):
            if "@" in new_email:
                res = requests.post(SHEET_SCRIPT_URL, json={"action": "add_contact", "email": new_email, "name": new_name})
                if res.status_code == 200: st.success("✅ 已加入 Contacts！")
            else: st.error("電郵格式錯誤")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 5. 永久除錯終端 ---
    st.markdown("---")
    with st.expander("🛠️ Firebean Brain Debug Terminal", expanded=False):
        if st.button("🔍 Test API Connection"): test_api_connection()
        if st.session_state.debug_logs:
            logs_html = "".join([f"<div class='debug-{l['type']}'>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.debug_logs)])
            st.markdown(f"<div class='debug-terminal'>{logs_html}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
