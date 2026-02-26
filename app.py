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

# --- 1. 核心配置與 Webhook URL ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycb6YNAjNNndamdkcULS71Q_qkkbclBViLlx9B8e7LaaxyapMc7jsgdvhMHZ3d_wLzXw/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbya_pl6h99zY_LrURojCL86c20NwxdeW6V9bhCXqgPjJdz2NVPgeFThthcR6gfw0d1P/exec"

# 🚀 使用最穩定的多模態模型
STABLE_MODEL_ID = "gemini-1.5-flash"

API_KEYS_POOL = [
    "AIzaSyA-5qXWjtzlUWP0IDMVUByMXdbylt8rTSA",
    "AIzaSyCVuoSuWV3tfGCu2tjikCkMOVRWCBFne20",
    "AIzaSyCZKtjLqN4FUQ76c3DYoDW20tTkFki_Rxk"
]

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Mission: PR Events bridge brands and audiences.
Rule: Analyze ALL uploaded photos to extract REAL visual facts (decor, scale, tech, crowd).
Strictly NO hallucinations. If Category is F&B, focus on food/hospitality seen in photos.
Always output JSON keys as numbered strings (e.g., '1_google_slide') for API sync.
"""

# --- 2. 核心邏輯 (Debug, API, Image) ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    """
    支援多相片分析的 SDK 調用，內置圖片壓縮防止 400 錯誤。
    """
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    all_keys = ([secret_key] if secret_key else []) + API_KEYS_POOL

    for idx, key in enumerate(all_keys):
        try:
            genai.configure(api_key=key)
            config = genai.types.GenerationConfig(
                response_mime_type="application/json" if is_json else "text/plain",
                temperature=0.3
            )
            model = genai.GenerativeModel(model_name=STABLE_MODEL_ID, system_instruction=FIREBEAN_SYSTEM_PROMPT)
            
            contents = [prompt]
            if image_files:
                for img_file in image_files:
                    # 🖼️ 智能壓縮：減輕 API 傳輸負擔
                    img = Image.open(img_file)
                    img.thumbnail((800, 800)) 
                    contents.append(img)
            
            response = model.generate_content(contents, generation_config=config)
            if response and response.text:
                log_debug(f"✅ API Success (Key #{idx})", "success")
                raw_text = response.text.strip()
                if not is_json: return raw_text
                # JSON 提取防爆
                json_match = re.search(r'(\[.*\]|\{.*\})', raw_text, re.DOTALL)
                return json_match.group(1) if json_match else raw_text
        except Exception as e:
            log_debug(f"❌ Key #{idx} Fail: {str(e)[:50]}", "warning")
            continue
    return None

def test_api_connection():
    """消失的 Check Key Function 回歸"""
    log_debug("🚀 開始連線測試...", "info")
    res = call_gemini_sdk("Ping. Please respond with: 'Firebean Online'.")
    if res:
        st.toast("✅ SDK 連線成功！")
        log_debug("系統連線正常，可執行 AI 診斷。", "success")
    else:
        st.toast("❌ 連線失敗，請檢查 Key 是否過期。")
        log_debug("API 沒反應，請檢查 Secrets 或金鑰池。", "error")

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
        # AI Manna 強化
        return ImageEnhance.Contrast(img).enhance(1.15)
    except: return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

def init_session_state():
    fields = {
        "active_tab": "📝 Project Collector",
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "who_we_help": ["GOVERNMENT & PUBLIC SECTOR"], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "project_photos": [], "hero_index": 0, "ai_content": {}, 
        "logo_white": "", "logo_black": "", "debug_logs": [], "mc_questions": [], 
        "open_question_ans": "", "visual_facts": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# --- 3. UI 樣式與進度顯示 ---

def get_animated_bar_html(percent, status_text):
    return f"""
    <div style="padding: 35px; background: #E0E5EC; border-radius: 20px; box-shadow: inset 8px 8px 16px #bec3c9, inset -8px -8px 16px #ffffff; margin: 25px 0; border: 1px solid rgba(255,0,0,0.1);">
        <div style="font-weight: 900; color: #FF0000; text-transform: uppercase; font-size: 22px; text-align: center; margin-bottom: 20px;">{status_text}</div>
        <div style="width: 100%; background: #d1d9e6; border-radius: 50px; height: 28px; position: relative; overflow: hidden; box-shadow: inset 4px 4px 8px #bec3c9;">
            <div style="width: {percent}%; background: linear-gradient(90deg, #FF0000, #b30000); height: 100%; border-radius: 50px; transition: width 0.3s ease-in-out;">
                <div style="position: absolute; width: 100%; text-align: center; color: white; font-weight: 900; font-size: 14px; line-height: 28px;">{percent}%</div>
            </div>
        </div>
    </div>
    """

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 110px; height: 110px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="110" height="110"><circle stroke="#d1d9e6" stroke-width="8" fill="transparent" r="45" cx="55" cy="55"/><circle stroke="#FF0000" stroke-width="8" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="45" cx="55" cy="55" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg>
            <div style="position: absolute; font-size: 20px; font-weight: 900; color: #2D3436;">{percent}%</div>
        </div>
    </div>"""

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 20px; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; padding: 25px; margin-bottom: 20px; }
        h1, h2, h3, label { color: #2D3436 !important; font-weight: 800 !important; }
        input, textarea, div[data-baseweb="select"] > div { background-color: #FFFFFF !important; border-radius: 10px !important; }
        .mc-question { font-weight: 700; color: #FF0000 !important; margin-top: 20px; border-left: 4px solid #FF0000; padding-left: 10px; }
        .debug-terminal { background: #1E1E1E !important; color: #00FF00 !important; padding: 15px; font-family: 'Courier New', monospace; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px; height: 180px; overflow-y: auto; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 10 維度進度計算
    score_items = ["client_name", "project_name", "venue", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    filled += (1 if len(st.session_state.mc_questions) == 20 else 0)
    total_pct = int((filled / 10) * 100)
    if total_pct > 100: total_pct = 100

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=160)
    with c2: st.markdown(get_circle_progress_html(total_pct), unsafe_allow_html=True)

    # 導航
    st.markdown("<br>", unsafe_allow_html=True)
    n1, n2, n3 = st.columns(3)
    tabs = ["📝 Project Collector", "📋 Review & Multi-Sync", "👥 CRM & Contacts"]
    for i, t in enumerate(tabs):
        if [n1, n2, n3][i].button(t, use_container_width=True, type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t
            st.rerun()
    st.markdown("---")

    # --- TAB 1: COLLECTOR ---
    if st.session_state.active_tab == "📝 Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Assets & Fact Info")
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Upload Black Logo", type=['png'], key="logo_b")
            if ub and st.button("Encode Black"): st.session_state.logo_black = standardize_logo(ub)
        with col2:
            uw = st.file_uploader("Upload White Logo", type=['png'], key="logo_w")
            if uw and st.button("Encode White"): st.session_state.logo_white = standardize_logo(uw)
        
        b1, b2, b3, b4 = st.columns(4)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b4.text_input("YouTube Link", st.session_state.youtube_link)
        
        c_a, c_b, c_c = st.columns(3)
        with c_a: 
            st.markdown("**👥 Category**")
            st.session_state.who_we_help = [st.radio("Cat", WHO_WE_HELP_OPTIONS, label_visibility="collapsed", index=WHO_WE_HELP_OPTIONS.index(st.session_state.who_we_help[0]) if st.session_state.who_we_help[0] in WHO_WE_HELP_OPTIONS else 0)]
        with c_b: 
            st.markdown("**🚀 What we do**")
            # 穩定 Checkbox 邏輯
            curr_wwd = []
            for opt in WHAT_WE_DO_OPTIONS:
                if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.what_we_do)): curr_wwd.append(opt)
            st.session_state.what_we_do = curr_wwd
        with c_c:
            st.markdown("**🛠️ Scope**")
            curr_sow = []
            for opt in SOW_OPTIONS:
                if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.scope_of_word)): curr_sow.append(opt)
            st.session_state.scope_of_word = curr_sow
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🧠 靈魂診斷官 (全相片分析 + 20 MC)")
            if st.button("🪄 執行全相片視覺分析並出題"):
                if not st.session_state.project_photos:
                    st.error("請先上傳活動相片作事實對位。")
                else:
                    loader = st.empty()
                    status = "📸 正在掃描全相片細節並獲取視覺事實..."
                    for p in range(0, 80, 5):
                        loader.markdown(get_animated_bar_html(p, status), unsafe_allow_html=True)
                        time.sleep(0.04)
                    
                    # 視覺分析提取事實
                    vision_prompt = """
                    Analyze these event photos collectively. Strictly report visual facts: 
                    Identify Branding colors, Tech used, Crowd density, and Catering service details if F&B. 
                    Be precise. Do not hallucinate historical heritage sites unless visible.
                    """
                    st.session_state.visual_facts = call_gemini_sdk(vision_prompt, image_files=st.session_state.project_photos)
                    
                    loader.markdown(get_animated_bar_html(90, "🧠 正在基於視覺證據生成題目..."), unsafe_allow_html=True)
                    
                    # 基於影像事實出題
                    prompt = f"""
                    你是 Firebean 診斷官。根據視覺實況：{st.session_state.visual_facts}
                    以及資料：Client: {st.session_state.client_name}, Venue: {st.session_state.venue}
                    生成 20 條 MC 題目。中心思想：透過 PR 體驗解決接觸不足問題。
                    Output STRICTLY JSON Array: [{{'id': 1, 'question': '...', 'options': ['A...', 'B...']}}]
                    """
                    res = call_gemini_sdk(prompt, is_json=True)
                    if res:
                        loader.markdown(get_animated_bar_html(100, "✅ 診斷題目已精準生成！"), unsafe_allow_html=True)
                        time.sleep(0.5); loader.empty()
                        try: st.session_state.mc_questions = json.loads(res)
                        except: st.error("JSON 解析錯誤")
                    else: loader.empty(); st.error("API 失敗，請重試或測試金鑰。")
            
            if st.session_state.mc_questions:
                for i, q in enumerate(st.session_state.mc_questions):
                    q_id = q.get('id', i + 1)
                    st.markdown(f"<div class='mc-question'>Q{q_id}. {q.get('question')}</div>", unsafe_allow_html=True)
                    sel = []
                    for opt_idx, opt_text in enumerate(q.get('options', [])):
                        if st.checkbox(opt_text, key=f"mc_cb_{q_id}_{opt_idx}"): sel.append(opt_text)
                    st.session_state[f"ans_{q_id}"] = sel
                st.session_state.open_question_ans = st.text_area("覺得我哋嘅概念最特別是什麼？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery")
            files = st.file_uploader("Upload Photos (min 4)", accept_multiple_files=True, key="photo_up")
            if files:
                st.session_state.project_photos = files
                hero = st.radio("🌟 Hero Banner", [f"P{i+1}" for i in range(len(files))], horizontal=True)
                st.session_state.hero_index = int(hero[1:]) - 1
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        img = manna_ai_enhance(f)
                        st.image(img, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if total_pct == 100:
            if st.button("🚀 資料已齊全！進入策略 Review", use_container_width=True, type="primary"):
                st.session_state.active_tab = "📋 Review & Multi-Sync"
                st.rerun()

    # --- TAB 2: REVIEW & SYNC ---
    elif st.session_state.active_tab == "📋 Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 2026 社交平台策略發布")
        
        if st.button("🪄 一鍵生成六大平台文案 (對接編號版)"):
            loader = st.empty()
            status = f"🧠 FIREBEAN BRAIN 正在分析全事實數據鏈..."
            for p in range(0, 96, 3): 
                loader.markdown(get_animated_bar_html(p, status), unsafe_allow_html=True)
                time.sleep(0.04)
            
            sum_ans = []
            for i, q in enumerate(st.session_state.mc_questions):
                ans = st.session_state.get(f"ans_{q.get('id', i+1)}", [])
                sum_ans.append(f"Q: {q.get('question')} | A: {', '.join(ans)}")
            
            # 🚀 關鍵：編號型 Key 確保與 Apps Script 100% 對接
            prompt = f"""
            作為 Strategist，根據事實：{st.session_state.visual_facts}
            執行數據：{chr(10).join(sum_ans)} | 概念：{st.session_state.open_question_ans}
            客戶: {st.session_state.client_name} | 項目: {st.session_state.project_name} | 地點: {st.session_state.venue}
            
            Output STRICTLY RAW JSON with these numbered keys:
            - "品牌痛點分析": text
            - "活動方案核心": text
            - "1_google_slide": {{ "hook": "...", "shift": "...", "proof": "..." }}
            - "2_facebook_post": text
            - "3_threads_post": text
            - "4_instagram_post": text (Traditional Chinese, <150 words)
            - "5_linkedin_post": text (Business English)
            - "6_website": {{ "en": "...", "tc": "...", "jp": "..." }}
            """
            res = call_gemini_sdk(prompt, is_json=True)
            if res:
                loader.markdown(get_animated_bar_html(100, "✅ 靈魂文案對位成功！"), unsafe_allow_html=True)
                time.sleep(0.5); loader.empty()
                try: 
                    st.session_state.ai_content = json.loads(res)
                    st.session_state.challenge = st.session_state.ai_content.get("品牌痛點分析", "")
                    st.session_state.solution = st.session_state.ai_content.get("活動方案核心", "")
                except: st.error("JSON 解析失敗")
            else: loader.empty(); st.error("API 失敗，請更換有效密鑰。")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync to Master Ecosystem", use_container_width=True, type="primary"):
                with st.spinner("🔄 正在多軌同步..."):
                    try:
                        ans_sync = []
                        if st.session_state.mc_questions:
                            for i, q in enumerate(st.session_state.mc_questions):
                                ans = st.session_state.get(f"ans_{q.get('id', i+1)}", [])
                                ans_sync.append(f"Q: {q.get('question')} | A: {', '.join(ans)}")
                        
                        payload = {
                            "action": "sync_project",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "client_name": st.session_state.client_name, "project_name": st.session_state.project_name,
                            "event_date": f"{st.session_state.event_year} {st.session_state.event_month}",
                            "venue": st.session_state.venue, "youtube_link": st.session_state.youtube_link,
                            "category_who": st.session_state.who_we_help[0],
                            "category_what": ", ".join(st.session_state.what_we_do),
                            "scope_of_work": ", ".join(st.session_state.scope_of_word),
                            "challenge": st.session_state.challenge, "solution": st.session_state.solution,
                            "open_question": st.session_state.open_question_ans,
                            "mc_summary": "\n".join(ans_sync), "ai_content": st.session_state.ai_content,
                            "logo_black": st.session_state.logo_black, "logo_white": st.session_state.logo_white,
                            "images": [base64.b64encode(f.getvalue()).decode() for f in st.session_state.project_photos]
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sheet Status: {r1.status_code}, Slide Status: {r2.status_code}", "success")
                        st.balloons(); st.success("✅ 同步成功！請檢查 Google Sheet & Slide。")
                    except Exception as e: log_debug(f"Sync Error: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 3: CRM ---
    elif st.session_state.active_tab == "👥 CRM & Contacts":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("👥 CRM 名單管理")
        e_em = st.text_input("Customer Email", key="crm_em")
        e_na = st.text_input("Name", key="crm_na")
        if st.button("📥 手動新增至 CRM"):
            if "@" in e_em:
                res = requests.post(SHEET_SCRIPT_URL, json={"action": "add_contact", "email": e_em, "name": e_na})
                if res.status_code == 200: st.success("✅ 已同步至 Contacts 工作表！")
            else: st.error("Email 格式錯誤")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 5. 永久除錯終端 ---
    with st.expander("🛠️ Firebean Brain Debug Terminal", expanded=False):
        col_t, _ = st.columns([1, 4])
        with col_t:
            if st.button("🔍 測試 API 連線"): test_api_connection()
        if st.session_state.debug_logs:
            logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.debug_logs)])
            st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
