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

# --- 1. 核心配置與 Webhook URL ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycb6YNAjNNndamdkcULS71Q_qkkbclBViLlx9B8e7LaaxyapMc7jsgdvhMHZ3d_wLzXw/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbya_pl6h99zY_LrURojCL86c20NwxdeW6V9bhCXqgPjJdz2NVPgeFThthcR6gfw0d1P/exec"

# 🚀 修正模型 ID：使用目前最穩定且具備 Vision 視覺能力的模型
STABLE_MODEL_ID = "gemini-2.0-flash"

# ⚠️ 已根據老細指示移除過期的後備金鑰池，現在系統將 100% 依賴你的 Secret Key
API_KEYS_POOL = [] 

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Mission: PR Events solve audience gaps through high-end experiences.
Rule: Analyze ALL uploaded photos to extract REAL visual facts (decor, scale, tech, crowd).
Language Rule: Always output in Traditional Chinese (繁體中文).
Sync Rule: Always output JSON using numbered keys (1_google_slide to 6_website) for API sync.
"""

# --- 2. 核心邏輯 (Debug, API, Image) ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    """
    優先讀取 Streamlit Secrets 中的 GEMINI_API_KEY。
    內置圖片壓縮與 JSON 提取保護。
    """
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    all_keys = ([secret_key] if secret_key else []) + API_KEYS_POOL

    if not all_keys:
        log_debug("🚨 錯誤：找不到任何 API Key！請在 Streamlit Secrets 設定 GEMINI_API_KEY。", "error")
        return None

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
                    # 處理 BytesIO (Dummy) 或 UploadedFile
                    img = Image.open(img_file)
                    img.thumbnail((800, 800)) # 🖼️ 壓縮相片防止 Payload 錯誤
                    contents.append(img)
            
            response = model.generate_content(contents, generation_config=config)
            if response and response.text:
                log_debug(f"✅ API 成功調用 (使用你的 Secret Key)", "success")
                raw_text = response.text.strip()
                if not is_json: return raw_text
                # 安全 JSON 提取
                json_match = re.search(r'(\[.*\]|\{.*\})', raw_text, re.DOTALL)
                return json_match.group(1) if json_match else raw_text
        except Exception as e:
            err_msg = str(e)
            if "401" in err_msg or "expired" in err_msg:
                log_debug("❌ API Key 失效或過期，請檢查 Secret Key 設定。", "error")
            elif "404" in err_msg:
                log_debug(f"❌ 模型 {STABLE_MODEL_ID} 未開放，請嘗試更換模型名。", "error")
            else:
                log_debug(f"⚠️ API 錯誤: {err_msg[:60]}", "warning")
            continue
    return None

def test_api_connection():
    log_debug("🚀 開始連線測試...", "info")
    res = call_gemini_sdk("Ping test. Please respond with: 'Firebean 2.0 Online'.")
    if res:
        st.toast("✅ SDK 連線成功！")
        log_debug("連線正常，可執行全功能同步。", "success")
    else:
        st.toast("❌ 連線失敗，請檢查 Secrets 中的 Key。", icon="🔥")

def standardize_logo(logo_file):
    try:
        raw = Image.open(logo_file)
        img = ImageOps.exif_transpose(raw).convert("RGBA")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

def create_dummy_image(color, label):
    """繪製測試用相片"""
    img = Image.new('RGB', (800, 600), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def create_dummy_logo_b64(bg_color):
    """繪製測試用 Logo 並轉為 Base64"""
    img = Image.new('RGBA', (400, 400), color=bg_color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def init_session_state():
    who_help_options = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
    fields = {
        "active_tab": "📝 Project Collector",
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "who_we_help": [who_help_options[0]], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "project_photos": [], "hero_index": 0, "ai_content": {}, 
        "logo_white": "", "logo_black": "", "debug_logs": [], "mc_questions": [], 
        "open_question_ans": "", "visual_facts": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def fill_dummy_data():
    """🚀 老細專屬：一鍵填充所有內容 (含相片、Logo、MC 答案)"""
    st.session_state.client_name = "Firebean 測試客戶"
    st.session_state.project_name = "2026 全功能同步測試項目"
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.youtube_link = "https://youtube.com/firebean"
    st.session_state.who_we_help = ["LIFESTYLE & CONSUMER"]
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope_of_word = ["Event Production", "Concept Development"]
    st.session_state.open_question_ans = "測試核心概念：透過一鍵自動化填充達成秒速測試。"
    st.session_state.visual_facts = "Dummy 分析：現場有大型 LED 幕、鮮豔紅色佈置。"
    
    # 自動生成 4 張相片
    st.session_state.project_photos = [
        create_dummy_image((255, 0, 0), "Photo 1"),
        create_dummy_image((0, 255, 0), "Photo 2"),
        create_dummy_image((0, 0, 255), "Photo 3"),
        create_dummy_image((255, 255, 0), "Photo 4")
    ]
    
    # 自動生成黑白 Logo
    st.session_state.logo_black = create_dummy_logo_b64((0,0,0,255))
    st.session_state.logo_white = create_dummy_logo_b64((255,255,255,255))
    
    # 自動生成 dummy MC 題目
    st.session_state.mc_questions = [
        {"id": 1, "question": "測試：系統同步是否正常？", "options": ["正常", "異常"]},
        {"id": 2, "question": "測試：視覺呈現是否滿意？", "options": ["滿意", "不滿意"]}
    ]
    st.session_state["ans_1"] = ["正常"]
    st.session_state["ans_2"] = ["滿意"]
    log_debug("🚀 一鍵自動化填充完成！可以直接去 Tab 2 試同步。", "success")

# --- 3. UI 樣式 ---

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 100px; height: 100px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="100" height="100"><circle stroke="#d1d9e6" stroke-width="8" fill="transparent" r="40" cx="50" cy="50"/><circle stroke="#FF0000" stroke-width="8" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg>
            <div style="position: absolute; font-size: 18px; font-weight: 900; color: #2D3436;">{percent}%</div>
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
        .mc-question { font-weight: 700; color: #FF0000 !important; margin-top: 15px; border-left: 4px solid #FF0000; padding-left: 10px; }
        .debug-terminal { background: #1E1E1E !important; color: #00FF00 !important; padding: 15px; font-family: 'Courier New', monospace; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    who_we_help_options = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
    what_we_do_options = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
    sow_options = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

    # Progress 計算
    score_items = ["client_name", "project_name", "venue", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    filled += (1 if len(st.session_state.mc_questions) >= 2 else 0)
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
        if [n1, n2, n3][i].button(t, use_container_width=True, key=f"nav_{i}", type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t
            st.rerun()
    st.markdown("---")

    # --- TAB 1: COLLECTOR ---
    if st.session_state.active_tab == "📝 Project Collector":
        if st.button("🧪 老細專屬：一鍵自動填充所有測試數據 (含圖片及 Logo)", use_container_width=True):
            fill_dummy_data()
            st.rerun()
        
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Assets & Fact Info")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.logo_black: st.success("✅ Black Logo Loaded")
            ub = st.file_uploader("Upload Black Logo", type=['png'], key="logo_b")
            if ub: st.session_state.logo_black = standardize_logo(ub)
        with col2:
            if st.session_state.logo_white: st.success("✅ White Logo Loaded")
            uw = st.file_uploader("Upload White Logo", type=['png'], key="logo_w")
            if uw: st.session_state.logo_white = standardize_logo(uw)
        
        b1, b2, b3, b4 = st.columns(4)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b4.text_input("YouTube Link", st.session_state.youtube_link)
        
        c_a, c_b, c_c = st.columns(3)
        with c_a: 
            st.markdown("**👥 Category**")
            st.session_state.who_we_help = [st.radio("Cat", who_we_help_options, label_visibility="collapsed", index=who_we_help_options.index(st.session_state.who_we_help[0]) if st.session_state.who_we_help[0] in who_we_help_options else 0)]
        with c_b: 
            st.markdown("**🚀 What we do**")
            st.session_state.what_we_do = [opt for opt in what_we_do_options if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.what_we_do))]
        with c_c:
            st.markdown("**🛠️ Scope**")
            st.session_state.scope_of_word = [opt for opt in sow_options if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.scope_of_word))]
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🧠 靈魂診斷官 (Gemini 2.0 Vision)")
            if st.button("🪄 生成 20 條繁中 MC 題目"):
                if not st.session_state.project_photos:
                    st.error("請先上傳活動相片。")
                else:
                    with st.spinner("📸 正在掃描全相片細節並生成題目..."):
                        vision_p = "Analyze event photos collectively. List visual facts (branding, crowd, tech) in Traditional Chinese."
                        st.session_state.visual_facts = call_gemini_sdk(vision_p, image_files=st.session_state.project_photos)
                        
                        # 使用雙括號防止 ValueError
                        prompt = f"""
                        你是 Firebean 診斷官。根據視覺實況：{st.session_state.visual_facts}
                        生成 20 條繁中 MC。中心思想：透過 PR 體驗解決接觸不足。
                        Output STRICTLY JSON Array: [{{"id": 1, "question": "...", "options": ["A", "B", "C", "D"]}}]
                        """
                        res = call_gemini_sdk(prompt, is_json=True)
                        if res:
                            parsed = json.loads(res)
                            if isinstance(parsed, list):
                                st.session_state.mc_questions = [q for q in parsed if isinstance(q, dict)]
            
            if st.session_state.mc_questions:
                for i, q in enumerate(st.session_state.mc_questions):
                    if isinstance(q, dict):
                        q_id = q.get('id', i + 1)
                        st.markdown(f"<div class='mc-question'>Q{q_id}. {q.get('question')}</div>", unsafe_allow_html=True)
                        sel = []
                        for opt_idx, opt_text in enumerate(q.get('options', [])):
                            val = opt_text in st.session_state.get(f"ans_{q_id}", [])
                            if st.checkbox(opt_text, key=f"mc_cb_{q_id}_{opt_idx}", value=val): sel.append(opt_text)
                        st.session_state[f"ans_{q_id}"] = sel
                st.session_state.open_question_ans = st.text_area("覺得概念最特別是什麼？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery")
            files = st.file_uploader("Upload Photos (min 4)", accept_multiple_files=True, key="photo_up")
            if files: st.session_state.project_photos = files
            
            if st.session_state.project_photos:
                cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with cols[i%4]:
                        img = Image.open(f)
                        st.image(img, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: REVIEW & SYNC ---
    elif st.session_state.active_tab == "📋 Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 社交平台對接策略")
        
        if st.button("🪄 生成六大對接文案 (Gemini 2.0)"):
            with st.spinner("🧠 FIREBEAN BRAIN 數據對位中..."):
                sum_ans = []
                for i, q in enumerate(st.session_state.mc_questions):
                    if isinstance(q, dict):
                        ans = st.session_state.get(f"ans_{q.get('id', i+1)}", [])
                        sum_ans.append(f"Q: {q.get('question')} | A: {', '.join(ans)}")
                
                prompt = f"""
                作為 Strategist，根據事實執行數據：{chr(10).join(sum_ans)}
                以及靈魂概念：{st.session_state.open_question_ans}
                Output STRICTLY RAW JSON with these numbered keys:
                - "品牌痛點分析": text (繁中)
                - "活動方案核心": text (繁中)
                - "1_google_slide": {{ "hook": "...", "shift": "...", "proof": "..." }}
                - "2_facebook_post": text
                - "3_threads_post": text
                - "4_instagram_post": text (繁中, <150字)
                - "5_linkedin_post": text
                - "6_website": {{ "en": "...", "tc": "...", "jp": "..." }}
                """
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    st.session_state.ai_content = json.loads(res)
                    st.session_state.challenge = st.session_state.ai_content.get("品牌痛點分析", "")
                    st.session_state.solution = st.session_state.ai_content.get("活動方案核心", "")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync (Sheet + Slide + Drive)", use_container_width=True, type="primary"):
                with st.spinner("🔄 同步中..."):
                    try:
                        mc_summary_text = []
                        for i, q in enumerate(st.session_state.mc_questions):
                            if isinstance(q, dict):
                                q_id = q.get('id', i+1)
                                ans = st.session_state.get(f"ans_{q_id}", [])
                                mc_summary_text.append(f"Q: {q.get('question')} | A: {', '.join(ans)}")
                        
                        sync_images = []
                        for f in st.session_state.project_photos:
                            f.seek(0)
                            sync_images.append(base64.b64encode(f.read()).decode())
                        
                        payload = {
                            "action": "sync_project",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue,
                            "category_who": st.session_state.who_we_help[0],
                            "category_what": ", ".join(st.session_state.what_we_do),
                            "scope_of_work": ", ".join(st.session_state.scope_of_word),
                            "mc_summary": "\n".join(mc_summary_text),
                            "open_question": st.session_state.open_question_ans,
                            "ai_content": st.session_state.ai_content,
                            "logo_black": st.session_state.logo_black,
                            "logo_white": st.session_state.logo_white,
                            "images": sync_images
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sheet Response: {r1.status_code}", "success")
                        st.balloons(); st.success("✅ 全部同步成功！")
                    except Exception as e: log_debug(f"Sync Error: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 3: CRM ---
    elif st.session_state.active_tab == "👥 CRM & Contacts":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("👥 CRM 名單管理")
        e_em = st.text_input("Customer Email", key="crm_em")
        e_na = st.text_input("Name", key="crm_na")
        if st.button("📥 手動新增"):
            if "@" in e_em:
                res = requests.post(SHEET_SCRIPT_URL, json={"action": "add_contact", "email": e_em, "name": e_na})
                if res.status_code == 200: st.success("✅ 已同步至 Contacts！")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 5. Debug 終端 ---
    with st.expander("🛠️ Firebean Brain Debug Terminal", expanded=False):
        if st.button("🔍 測試 API 連線"): test_api_connection()
        if st.session_state.debug_logs:
            logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.debug_logs)])
            st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
