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
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw5Bf3CsEYZJCEVzgzS_pSwg8y0B69iHLDywgZyz45ctsZTShe1YxRiTTKGjiMc1HFe/exec"

# 🔑 從 Streamlit Secrets 讀取 API Key (Settings -> Secrets: API_KEYS = ["..."])
API_KEYS_POOL = st.secrets.get("API_KEYS", [])

# 鎖死所有選項
WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = [
    "Event Planning", "Event Coordination", "Event Production", "Theme Design", 
    "Concept Development", "Social Media Management", "KOL / MI Line up", 
    "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"
]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
LinkedIn/Slides: Professional Business English. IG/Threads: Canto-slang. Website: Trilingual.
Motto: 'Turn Policy into Play'. 
Strictly NO Simplified Chinese. All Challenge/Solution sections must be 50-100 words.
"""

# --- 2. 核心功能引擎 (SDK 輪詢) ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False, dynamic_sys_prompt=None):
    if not API_KEYS_POOL:
        log_debug("🚨 找不到 API Keys！", "error")
        return None
    sys_instruction = dynamic_sys_prompt if dynamic_sys_prompt else FIREBEAN_SYSTEM_PROMPT
    for idx, key in enumerate(API_KEYS_POOL):
        try:
            log_debug(f"Attempting API with Key #{idx+1}...", "info")
            genai.configure(api_key=key)
            generation_config = genai.types.GenerationConfig(response_mime_type="application/json" if is_json else "text/plain")
            model = genai.GenerativeModel(model_name="gemini-2.0-flash", system_instruction=sys_instruction)
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

def test_api_connection():
    res = call_gemini_sdk("Ping test. Respond with: 'Firebean 2.0 Online.'")
    if res: st.toast("✅ SDK 連線成功！")
    else: st.toast("❌ 連線失敗", icon="🔥")

# --- 3. 影像處理功能 (Manna AI) ---

def standardize_logo(logo_file):
    try:
        raw = Image.open(logo_file)
        img = ImageOps.exif_transpose(raw).convert("RGBA")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

def manna_ai_enhance(image_file):
    log_debug(f"Vision Processing: {image_file.name}")
    with st.spinner("🚀 Manna AI 正在校正轉向並同步視角..."):
        try:
            raw_img = Image.open(image_file)
            img = ImageOps.exif_transpose(raw_img).convert("RGB")
            img_enhanced = ImageEnhance.Contrast(img).enhance(1.15)
            call_gemini_sdk("Analyze this photo.", image_file=img)
            return img_enhanced
        except Exception: return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

# --- 4. UI 視覺樣式與狀態管理 ---

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
        .debug-warning { color: #FFFF55; }
        </style>
    """, unsafe_allow_html=True)

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""<div style="display: flex; justify-content: flex-end; align-items: center;"><div style="position: relative; width: 130px; height: 130px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;"><svg width="130" height="130"><circle stroke="#d1d9e6" stroke-width="10" fill="transparent" r="55" cx="65" cy="65"/><circle stroke="#FF0000" stroke-width="10" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="55" cx="65" cy="65" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg><div style="position: absolute; font-size: 26px; font-weight: 900; color: #2D3436;">{percent}%</div></div></div>"""

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "messages": [{"role": "assistant", "content": "Firebean Brain Online. 我係你嘅專屬 PR Director。分享下最初 Client 遇到最大嘅 Challenge (痛點) 係咩？"}],
        "project_photos": [], "hero_index": 0, "processed_photos": {}, "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": []
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def sync_to_master_db(ai_results):
    """鎖死 A-T 欄同步映射邏輯"""
    try:
        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "client_name": st.session_state.client_name,
            "project_name": st.session_state.project_name,
            "event_date": f"{st.session_state.event_year} {st.session_state.event_month}",
            "venue": st.session_state.venue,
            "category_who": ", ".join(st.session_state.who_we_help),
            "category_what": ", ".join(st.session_state.what_we_do),
            "scope_of_work": ", ".join(st.session_state.scope_of_word), # H 欄工作範疇
            "youtube_link": st.session_state.youtube_link,
            "challenge": ai_results.get("6_website", {}).get("tc", {}).get("content", ""),
            "solution": ai_results.get("6_website", {}).get("tc", {}).get("content", ""),
            "ai_content": ai_results 
        }
        res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=30)
        return res.status_code == 200
    except Exception as e:
        log_debug(f"Sync failed: {str(e)}", "error")
        return False

# --- 5. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 進度計算 (12 維度)
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
        # --- 核心資料區 ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Core Information")
        b1, b2, b3_y, b3_m, b4, b5 = st.columns([1, 1, 0.5, 0.4, 1, 1])
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("Year", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("Month", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.venue = b4.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b5.text_input("YouTube Link", st.session_state.youtube_link)
        
        # --- 🔥 SOW 改為 Checkbox 機制 🔥 ---
        st.write("🛠️ **Scope of Work (SOW)** - [剔選適用工作範圍]")
        s_cols = st.columns(3)
        selected_sow = []
        for i, option in enumerate(SOW_OPTIONS):
            is_checked = option in st.session_state.scope_of_word
            if s_cols[i % 3].checkbox(option, value=is_checked, key=f"sow_{option}"):
                selected_sow.append(option)
        st.session_state.scope_of_word = selected_sow # 更新狀態以備同步
        
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 PR Director Chatbot")
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])
            if p := st.chat_input("向 PR Director 匯報..."):
                st.session_state.messages.append({"role": "user", "content": p})
                # 加入進度感知 Prompt
                res = call_gemini_sdk(f"Progress: {percent}%. User says: {p}")
                st.session_state.messages.append({"role": "assistant", "content": res})
                st.rerun()
            if st.button("⏹️ 強制結束訪談並生成文案"):
                res_json = call_gemini_sdk("FORCE GENERATE MASTER JSON NOW.", is_json=True)
                if res_json: st.session_state.ai_content = json.loads(res_json); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Require 4+ Photos)")
            files = st.file_uploader("Upload Photos", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                h_idx = min(st.session_state.hero_index, len(files)-1)
                hero_choice = st.radio("🌟 Hero Banner", [f"P{i+1}" for i in range(len(files))], index=h_idx, horizontal=True)
                st.session_state.hero_index = int(hero_choice[1:]) - 1
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        if st.button(f"🪄 AI P{i+1}", key=f"ai_{i}"): st.session_state.processed_photos[i] = manna_ai_enhance(f); st.rerun()
                        img_disp = st.session_state.processed_photos.get(i, ImageOps.exif_transpose(Image.open(f)))
                        border = "hero-border" if i == st.session_state.hero_index else ""
                        st.markdown(f'<div class="{border}">', unsafe_allow_html=True)
                        st.image(img_disp, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Platform Content Generation")
        
        st.session_state.challenge = st.text_area("Boring Challenge (EN)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Creative Solution (EN)", st.session_state.solution)

        if st.button("🪄 一鍵生成六大平台文案 (數據注入)"):
            with st.spinner("🧠 正在根據輸入資料生成專屬文案..."):
                gen_prompt = f"""
                BASED ONLY ON PROJECT: {st.session_state.project_name} for Client: {st.session_state.client_name}.
                Challenge: {st.session_state.challenge}
                Solution: {st.session_state.solution}
                Generate JSON for Slides, Socials, Website (EN, TC, JP). NO Simplified Chinese. 50-100 words.
                """
                res_json = call_gemini_sdk(gen_prompt, is_json=True)
                if res_json: st.session_state.ai_content = json.loads(res_json); st.success("✅ 生成完畢！")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync to Master Ecosystem"):
                if sync_to_master_db(st.session_state.ai_content):
                    st.balloons(); st.success("✅ 包含 A-T 欄數據與 SOW 已成功同步！")
        st.markdown('</div>', unsafe_allow_html=True)

    # 永久除錯終端
    st.markdown("---")
    with st.expander("🛠️ Debug Terminal", expanded=False):
        if st.button("🔍 Test API Connection"): test_api_connection()
        if st.session_state.debug_logs:
            for l in reversed(st.session_state.debug_logs):
                cls = f"debug-{l['type']}"
                st.markdown(f"<div class='debug-terminal {cls}'>[{l['time']}] {l['msg']}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
