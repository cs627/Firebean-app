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

# 🚀 鎖定模型 ID
STABLE_MODEL_ID = "gemini-2.5-flash"

# 只使用老細 Secrets 中的 Key
API_KEYS_POOL = [] 

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Philosophy: PR Events solve brand-audience gaps through high-end experiences.
Language Rule: Always output in Traditional Chinese (繁體中文).
Sync Rule: Always output JSON using numbered keys (1_google_slide to 6_website) for API sync.
Fact Rule: Analyze all photos provided strictly. No hallucinations.
"""

# --- 2. 核心邏輯 (Debug, API, Image) ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    """Gemini 2.5 SDK 調用，內置高強度壓縮防超時"""
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key:
        log_debug("🚨 錯誤：找不到 Secret Key！請在 Secrets 設定 GEMINI_API_KEY。", "error")
        return None

    try:
        genai.configure(api_key=secret_key)
        config = genai.types.GenerationConfig(
            response_mime_type="application/json" if is_json else "text/plain",
            temperature=0.3
        )
        model = genai.GenerativeModel(model_name=STABLE_MODEL_ID, system_instruction=FIREBEAN_SYSTEM_PROMPT)
        
        contents = [prompt]
        if image_files:
            for img_file in image_files:
                img = Image.open(img_file)
                img.thumbnail((800, 800))
                contents.append(img)
        
        response = model.generate_content(contents, generation_config=config)
        if response and response.text:
            log_debug(f"✅ Gemini 2.5 調用成功", "success")
            raw_text = response.text.strip()
            if not is_json: return raw_text
            json_match = re.search(r'(\[.*\]|\{.*\})', raw_text, re.DOTALL)
            return json_match.group(1) if json_match else raw_text
    except Exception as e:
        log_debug(f"❌ Gemini 2.5 出錯: {str(e)[:100]}", "error")
    return None

def test_api_connection():
    log_debug("🚀 開始連線測試...", "info")
    res = call_gemini_sdk("Ping test. Please respond exactly with: 'Firebean 2.5 Online'.")
    if res:
        st.toast("✅ SDK 連線成功！Gemini 2.5 已 Ready。")
        log_debug("系統連線正常，可執行全功能同步。", "success")
    else:
        st.toast("❌ 連線失敗，請檢查 Secrets 中的 Key。", icon="🔥")

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    d = ImageDraw.Draw(img)
    d.text((50, 50), label, fill=(255,255,255))
    buf = io.BytesIO(); img.save(buf, format="JPEG"); buf.seek(0)
    return buf

def create_dummy_logo_b64(bg_color):
    img = Image.new('RGBA', (400, 400), color=bg_color)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def fill_dummy_data():
    """老細專屬：全自動填寫測試數據 (文字 + 相片 + Logo + MC)"""
    st.session_state.client_name = "Firebean 測試機構"
    st.session_state.project_name = "2026 全自動同步展覽"
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.youtube_link = "https://youtube.com/firebean-test"
    st.session_state.who_we_help = ["LIFESTYLE & CONSUMER"]
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope_of_word = ["Theme Design", "Concept Development", "Event Production"]
    st.session_state.open_question_ans = "測試核心概念：透過一鍵自動化填充達成秒速測試同步邏輯。"
    st.session_state.visual_facts = "Dummy 分析：現場有大型互動幕牆、鮮豔紅色品牌調性。"
    
    # 生成 4 張相片
    colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0)]
    st.session_state.project_photos = [create_dummy_image(c, f"Photo {i+1}") for i, c in enumerate(colors)]
    
    # 生成 Logo
    st.session_state.logo_black = create_dummy_logo_b64((0,0,0,255))
    st.session_state.logo_white = create_dummy_logo_b64((255,255,255,255))
    
    # 生成 Dummy MC
    st.session_state.mc_questions = [
        {"id": 1, "question": "測試：系統同步是否正常？", "options": ["正常", "異常"]},
        {"id": 2, "question": "測試：文案是否準確？", "options": ["準確", "一般"]}
    ]
    st.session_state["ans_1"] = ["正常"]
    st.session_state["ans_2"] = ["準確"]
    log_debug("🚀 已自動填充文字、Dummy 相片及測試 Logo！", "success")

def init_session_state():
    fields = {
        "active_tab": "📝 Project Collector",
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "who_we_help": [WHO_WE_HELP_OPTIONS[0]], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "project_photos": [], "hero_index": 0, "ai_content": {}, 
        "logo_white": "", "logo_black": "", "debug_logs": [], "mc_questions": [], 
        "open_question_ans": "", "visual_facts": "", "challenge": "", "solution": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

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

    # Progress
    score_items = ["client_name", "project_name", "venue", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    filled += (1 if len(st.session_state.mc_questions) >= 2 else 0)
    total_pct = min(100, int((filled / 10) * 100))

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=160)
    with c2: st.markdown(get_circle_progress_html(total_pct), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    n1, n2, n3 = st.columns(3)
    tab_list = ["📝 Project Collector", "📋 Review & Multi-Sync", "👥 CRM & Contacts"]
    for i, t in enumerate(tab_list):
        if [n1, n2, n3][i].button(t, use_container_width=True, key=f"nav_{i}", type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t
            st.rerun()
    st.markdown("---")

    if st.session_state.active_tab == "📝 Project Collector":
        if st.button("🧪 老細專用：一鍵填充測試數據 (文字 + 相片 + Logo)", use_container_width=True):
            fill_dummy_data(); st.rerun()
        
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Assets & Fact Info")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.logo_black: st.success("✅ Black Logo Ready")
            ub = st.file_uploader("Upload Black Logo", type=['png'], key="logo_b")
            if ub:
                img_data = ub.read()
                st.session_state.logo_black = base64.b64encode(img_data).decode()
        with col2:
            if st.session_state.logo_white: st.success("✅ White Logo Ready")
            uw = st.file_uploader("Upload White Logo", type=['png'], key="logo_w")
            if uw:
                img_data = uw.read()
                st.session_state.logo_white = base64.b64encode(img_data).decode()
        
        b1, b2, b3, b4 = st.columns(4)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b4.text_input("YouTube", st.session_state.youtube_link)

        c_a, c_b, c_c = st.columns(3)
        with c_a: 
            st.markdown("**👥 Category**")
            st.session_state.who_we_help = [st.radio("Cat", WHO_WE_HELP_OPTIONS, label_visibility="collapsed", index=WHO_WE_HELP_OPTIONS.index(st.session_state.who_we_help[0]) if st.session_state.who_we_help[0] in WHO_WE_HELP_OPTIONS else 0)]
        with c_b: 
            st.markdown("**🚀 What we do**")
            st.session_state.what_we_do = [opt for opt in WHAT_WE_DO_OPTIONS if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.what_we_do))]
        with c_c:
            st.markdown("**🛠️ SOW (Scope of Work)**")
            st.session_state.scope_of_word = [opt for opt in SOW_OPTIONS if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.scope_of_word))]
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🧠 靈魂診斷官 (Gemini 2.5 Vision)")
            if st.button("🪄 生成 20 條繁中 MC 題目 (全相片分析)"):
                if not st.session_state.project_photos: st.error("請上傳或生成相片。")
                else:
                    with st.spinner("Gemini 2.5 掃描中..."):
                        vision_p = "Collectively analyze event photos. List visual facts (branding, crowd, tech) in Traditional Chinese."
                        st.session_state.visual_facts = call_gemini_sdk(vision_p, image_files=st.session_state.project_photos)
                        
                        # 🚀 雙括號防止 ValueError
                        prompt = f"""
                        你是 Firebean 診斷官。根據視覺實況：{st.session_state.visual_facts}
                        生成 20 條繁中 MC 題目。中心思想：透過 PR 體驗解決接觸不足。
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
                        ans_key = f"ans_{q_id}"
                        sel = []
                        for opt_idx, opt_text in enumerate(q.get('options', [])):
                            val = opt_text in st.session_state.get(ans_key, [])
                            if st.checkbox(opt_text, key=f"mc_cb_{q_id}_{opt_idx}", value=val): sel.append(opt_text)
                        st.session_state[ans_key] = sel
                st.session_state.open_question_ans = st.text_area("覺得概念最特別是什麼？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery")
            files = st.file_uploader("Upload Photos", accept_multiple_files=True)
            if files: st.session_state.project_photos = files
            if st.session_state.project_photos:
                cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with cols[i%4]:
                        img = Image.open(f)
                        st.image(img, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.active_tab == "📋 Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("🪄 生成六大平台對接文案 (Gemini 2.5)"):
            with st.spinner("🧠 FIREBEAN BRAIN 對位中..."):
                sum_ans = []
                for i, q in enumerate(st.session_state.mc_questions):
                    if isinstance(q, dict):
                        ans = st.session_state.get(f"ans_{q.get('id', i+1)}", [])
                        sum_ans.append(f"Q: {q.get('question')} | A: {', '.join(ans)}")
                
                prompt = f"""
                Strategist 分析事實執行數據：{chr(10).join(sum_ans)}
                以及視覺事實：{st.session_state.visual_facts}
                以及概念：{st.session_state.open_question_ans}
                Output STRICTLY RAW JSON with numbering keys for API sync:
                - "1_google_slide": {{ "hook": "...", "shift": "...", "proof": "..." }}
                - "2_facebook_post": text
                - "3_threads_post": text
                - "4_instagram_post": text (繁中, <150字)
                - "5_linkedin_post": text
                - "6_website": {{ "en": "...", "tc": "...", "jp": "..." }}
                - "品牌痛點分析": text, "活動方案核心": text
                """
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    st.session_state.ai_content = json.loads(res)
                    st.session_state.challenge = st.session_state.ai_content.get("品牌痛點分析", "")
                    st.session_state.solution = st.session_state.ai_content.get("活動方案核心", "")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync (Sheet + Slide + Drive)", use_container_width=True, type="primary"):
                with st.spinner("🔄 多軌同步中..."):
                    try:
                        mc_summary_text = []
                        for i, q in enumerate(st.session_state.mc_questions):
                            if isinstance(q, dict):
                                q_id = q.get('id', i+1)
                                ans = st.session_state.get(f"ans_{q_id}", [])
                                mc_summary_text.append(f"Q: {q.get('question')} | A: {', '.join(ans)}")
                        
                        sync_imgs = []
                        for f in st.session_state.project_photos:
                            f.seek(0); sync_imgs.append(base64.b64encode(f.read()).decode())
                        
                        payload = {
                            "action": "sync_project", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "client_name": st.session_state.client_name, "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue, "category_who": st.session_state.who_we_help[0],
                            "category_what": ", ".join(st.session_state.what_we_do),
                            "scope_of_work": ", ".join(st.session_state.scope_of_word),
                            "mc_summary": "\n".join(mc_summary_text),
                            "open_question": st.session_state.open_question_ans, "ai_content": st.session_state.ai_content,
                            "challenge": st.session_state.challenge, "solution": st.session_state.solution,
                            "logo_black": st.session_state.logo_black, "logo_white": st.session_state.logo_white, "images": sync_imgs
                        }
                        # 🚀 送出前打印 Payload 狀態
                        log_debug(f"Payload Size: {len(str(payload))} bytes", "info")
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sheet Response: {r1.status_code}, Slide Response: {r2.status_code}", "success")
                        st.balloons(); st.success("✅ 全部數據同步成功！")
                    except Exception as e: log_debug(f"Sync Error: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("🛠️ Debug Terminal", expanded=False):
        if st.button("🔍 測試 API 連線"): test_api_connection()
        logs_html = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.debug_logs)])
        st.markdown(f"<div class='debug-terminal'>{logs_html}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
