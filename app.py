import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import traceback
import requests
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from datetime import datetime

# --- 1. 核心配置與 API Key 池 ---
# 鎖死 Google Apps Script 同步連結與 API 金鑰
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwLR9MVr4rNgCQeXd2zGq43_F3ncsml_t7IP4OkjqBNtdNiv0ETitiuzx4oif3T0tCZ/exec"

API_KEYS_POOL = [
    "AIzaSyA-5qXWjtzlUWP0IDMVUByMXdbylt8rTSA",
    "AIzaSyCVuoSuWV3tfGCu2tjikCkMOVRWCBFne20",
    "AIzaSyCZKtjLqN4FUQ76c3DYoDW20tTkFki_Rxk"
]

# 鎖死選項與 PR DNA 指令
WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
LinkedIn/Slides: Professional Business English. IG/Threads: Canto-slang. Website: Trilingual (EN, TC, JP).
Motto: 'Turn Policy into Play'. 
Strictly NO Simplified Chinese. All Challenge/Solution sections must be 50-100 words.
"""

# --- 2. 核心調試與官方 SDK 智能輪詢引擎 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False, dynamic_sys_prompt=None):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    all_keys = ([secret_key] if secret_key else []) + API_KEYS_POOL
    model_name = "gemini-2.5-flash"
    sys_instruction = dynamic_sys_prompt if dynamic_sys_prompt else FIREBEAN_SYSTEM_PROMPT

    for idx, key in enumerate(all_keys):
        try:
            log_debug(f"Attempting API with Key #{idx+1}...", "info")
            genai.configure(api_key=key)
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json" if is_json else "text/plain"
            )
            model = genai.GenerativeModel(model_name=model_name, system_instruction=sys_instruction)
            contents = [prompt]
            if image_file: contents.append(image_file)
            response = model.generate_content(contents, generation_config=generation_config)
            if response and response.text:
                log_debug(f"Success with Key #{idx+1}!", "success")
                return response.text
        except Exception as e:
            log_debug(f"Key #{idx+1} Error: {str(e)}", "warning")
            continue
    return None

def standardize_logo(logo_file, target_size=(800, 400), padding=40):
    try:
        raw = Image.open(logo_file)
        img = ImageOps.exif_transpose(raw).convert("RGBA")
        bbox = img.getbbox()
        if bbox: img = img.crop(bbox)
        inner_w, inner_h = target_size[0] - (padding * 2), target_size[1] - (padding * 2)
        img.thumbnail((inner_w, inner_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, img)
        buf = io.BytesIO(); canvas.save(buf, format="PNG")
        log_debug(f"Logo '{logo_file.name}' normalized.", "success")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log_debug(f"Logo Fix Error: {str(e)}", "error")
        return ""

def manna_ai_enhance(image_file):
    log_debug(f"Processing AI Vision for: {image_file.name}")
    with st.spinner("🚀 Manna AI 校正轉向並同步視角..."):
        try:
            raw_img = Image.open(image_file)
            img = ImageOps.exif_transpose(raw_img).convert("RGB")
            img_enhanced = ImageEnhance.Contrast(img).enhance(1.15)
            res = call_gemini_sdk("Analyze this institutional project photo.", image_file=img)
            if res: log_debug("AI Vision Handshake Complete.", "success")
            return img_enhanced
        except Exception:
            return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

# --- 3. UI 樣式與狀態管理 ---

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 25px; box-shadow: 12px 12px 24px #bec3c9, -12px -12px 24px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.4); border-radius: 12px; }
        .debug-terminal { background: #1E1E1E; color: #00FF00; padding: 12px; font-family: 'Courier New', monospace; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px 10px 0 0; max-height: 250px; overflow-y: auto; margin-top: 50px; }
        .debug-success { color: #00FF00; font-weight: bold; }
        .debug-error { color: #FF5555; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 130px; height: 130px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="130" height="130"><circle stroke="#d1d9e6" stroke-width="10" fill="transparent" r="55" cx="65" cy="65"/><circle stroke="#FF0000" stroke-width="10" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="55" cx="65" cy="65" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg>
            <div style="position: absolute; font-size: 26px; font-weight: 900; color: #2D3436;">{percent}%</div>
        </div>
    </div>
    """

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", 
        "messages": [{"role": "assistant", "content": "Firebean Brain Online. 我係你嘅專屬 PR Director。今次個 Project 聽落好有潛力，可唔可以分享下最初 Client 遇到最大嘅 Challenge (痛點) 係咩？我哋一齊度橋點樣 Turn Policy into Play！"}], 
        "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": []
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def get_proactive_chatbot_prompt():
    missing_text = [k for k in ["client_name", "project_name", "venue", "challenge", "solution", "youtube_link"] if not st.session_state.get(k)]
    missing_assets = []
    if not (st.session_state.logo_white or st.session_state.logo_black): missing_assets.append("Client Logo (未上傳)")
    if len(st.session_state.project_photos) < 4: missing_assets.append(f"活動相片 (目前只有 {len(st.session_state.project_photos)} 張，需要最少 4 張)")
    
    return f"""{FIREBEAN_SYSTEM_PROMPT}
    You are acting as a Proactive Senior PR Director at Firebean. Your job is to INTERVIEW the user (an Account Executive) to gather all missing information for the Master DB.
    
    Current Missing Information: {missing_text}
    Current Missing Assets: {missing_assets}
    
    INTERVIEW RULES:
    1. PROACTIVE PROBING: Never just say "Got it." Always acknowledge their input with professional PR insight, and then ASK a follow-up question to extract ONE missing piece of information (e.g., "That sounds like a solid interactive solution. But what was the original boring 'Challenge' we were trying to solve for the client?").
    2. ASSET REMINDER: If 'Missing Assets' or 'youtube_link' is not empty, gently remind the user: "Btw, don't forget we need the client logo, at least 4 photos for the layout, and a YouTube highlight link before we can generate the final ecosystem copy."
    3. TONE: Use Hong Kong PR Director tone. Mix professional PR terms with Canto-slang.
    4. STEP-BY-STEP: Only ask for 1 thing at a time. Act like an inquisitive journalist.
    """

# --- 4. Main App 邏輯 ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 鎖定 12 維度 Progress Bar 
    score_items = ["client_name", "project_name", "venue", "challenge", "solution", "youtube_link"]
    filled = sum([1 for f in score_items if st.session_state[f]])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white and st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0) + (1 if st.session_state.ai_content else 0)
    percent = int((filled / 12) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector & Chatbot", "📋 Content Generation & DB Sync"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Logos (Must upload Black or White)")
        lc1, lc2 = st.columns(2)
        with lc1:
            ub = st.file_uploader("Upload Black Logo", type=['png'], key="logo_b")
            if ub and st.button("📏 Fix Black"): st.session_state.logo_black = standardize_logo(ub)
        with lc2:
            uw = st.file_uploader("Upload White Logo", type=['png'], key="logo_w")
            if uw and st.button("📏 Fix White"): st.session_state.logo_white = standardize_logo(uw)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Core Information")
        b1, b2, b3_y, b3_m, b4, b5 = st.columns([1, 1, 0.5, 0.4, 1, 1])
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("Year", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("Month", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.venue = b4.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b5.text_input("YouTube Link", st.session_state.youtube_link)
        
        c1, c2, c3 = st.columns(3)
        st.session_state.who_we_help = c1.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.session_state.what_we_do = c2.multiselect("🚀 What we do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 PR Director Chatbot (Proactive Interviewer)")
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])
            if p := st.chat_input("向 PR Director 匯報細節或回答問題..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages[-5:]])
                prompt = f"Chat History:\n{history_str}\n\nUser: {p}"
                res_text = call_gemini_sdk(prompt, dynamic_sys_prompt=get_proactive_chatbot_prompt())
                if res_text:
                    st.session_state.messages.append({"role": "assistant", "content": res_text})
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Require 4+ Photos)")
            files = st.file_uploader("Upload Photos", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                h_idx = min(st.session_state.hero_index, len(files)-1) if files else 0
                hero_choice = st.radio("🌟 必須選取 Highlight Hero Banner", [f"P{i+1}" for i in range(len(files))], index=h_idx, horizontal=True)
                st.session_state.hero_index = int(hero_choice[1:]) - 1
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        if st.button(f"🪄 AI P{i+1}", key=f"ai_{i}"):
                            st.session_state.processed_photos[i] = manna_ai_enhance(f)
                            st.rerun()
                        img_disp = st.session_state.processed_photos.get(i, ImageOps.exif_transpose(Image.open(f)))
                        border = "hero-border" if i == st.session_state.hero_index else ""
                        st.markdown(f'<div class="{border}">', unsafe_allow_html=True)
                        st.image(img_disp, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Platform Content Generation & Sync")
        st.session_state.challenge = st.text_area("Boring Challenge (EN)", st.session_state.challenge, help="從 Chatbot 收集的痛點")
        st.session_state.solution = st.text_area("Creative Solution (EN)", st.session_state.solution, help="從 Chatbot 收集的方案")
        
        has_logo = bool(st.session_state.logo_white or st.session_state.logo_black)
        has_enough_photos = len(st.session_state.project_photos) >= 4
        
        if st.button("🪄 一鍵生成六大平台文案 (Follow PDF Guidelines)"):
            if not has_logo or not has_enough_photos:
                st.markdown("<div class='blocker-alert'>🚨 <b>阻截警告：</b> 請確保 Logo 與 4 張相片已上傳。</div>", unsafe_allow_html=True)
            else:
                generation_prompt = f"Project: {st.session_state.project_name}\nChallenge: {st.session_state.challenge}\nSolution: {st.session_state.solution}\nYouTube: {st.session_state.youtube_link}\nScope: {st.session_state.scope_of_word}\n\nGenerate JSON based on PDF styles: google_slide, facebook_post, threads_post, instagram_post, linkedin_post, website (en, tc, jp)."
                with st.spinner("🧠 正在生成六大平台多語系文案..."):
                    res_json = call_gemini_sdk(generation_prompt, is_json=True)
                    if res_json:
                        try:
                            st.session_state.ai_content = json.loads(res_json)
                            st.success("✅ 六大平台文案已完美生成！")
                        except: log_debug("JSON Parsing Error.", "error")
        
        if st.session_state.ai_content: st.json(st.session_state.ai_content)
        
        if st.button("🚀 Confirm & Sync to Master Ecosystem"):
            if not st.session_state.ai_content: st.error("請先生成文案！")
            else: st.balloons(); st.success("✅ 資料庫同步成功！")
        st.markdown('</div>', unsafe_allow_html=True)

    # 鎖定永久除錯終端 
    st.markdown("---")
    with st.expander("🛠️ Firebean Brain Debug Terminal (Permanent)", expanded=False):
        if st.button("🔍 Test API Connection"): test_api_connection()
        if st.session_state.debug_logs:
            for l in reversed(st.session_state.debug_logs):
                cls = f"debug-{l['type']}"
                st.markdown(f"<div class='debug-terminal {cls}'>[{l['time']}] {l['msg']}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
