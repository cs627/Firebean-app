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

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw5Bf3CsEYZJCEVzgzS_pSwg8y0B69iHLDywgZyz45ctsZTShe1YxRiTTKGjiMc1HFe/exec"
API_KEYS_POOL = st.secrets.get("API_KEYS", [])

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
Motto: 'Turn Policy into Play'. 
Strictly NO Simplified Chinese. All Challenge/Solution sections must be 50-100 words.
Output ONLY in EN, TC (Traditional Chinese), and JP. 
"""

# --- 2. 核心功能引擎 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False, dynamic_sys_prompt=None):
    if not API_KEYS_POOL:
        log_debug("🚨 API Keys Missing!", "error")
        return None
    sys_instruction = dynamic_sys_prompt if dynamic_sys_prompt else FIREBEAN_SYSTEM_PROMPT
    for idx, key in enumerate(API_KEYS_POOL):
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name="gemini-2.0-flash", system_instruction=sys_instruction)
            config = genai.types.GenerationConfig(response_mime_type="application/json" if is_json else "text/plain")
            contents = [prompt]
            if image_file: contents.append(image_file)
            response = model.generate_content(contents, generation_config=config)
            if response and response.text: return response.text
        except Exception as e:
            log_debug(f"Key #{idx+1} Error: {str(e)}", "warning")
            continue
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

# --- 3. UI 視覺樣式與狀態 ---

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 25px; box-shadow: 12px 12px 24px #bec3c9, -12px -12px 24px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.4); border-radius: 12px; }
        .debug-terminal { background: #1E1E1E; color: #00FF00; padding: 10px; font-family: monospace; font-size: 11px; }
        </style>
    """, unsafe_allow_html=True)

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "messages": [{"role": "assistant", "content": "Director Online. 請問餐廳遇到嘅挑戰係咩？"}],
        "project_photos": [], "hero_index": 0, "processed_photos": {}, "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": []
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def sync_to_master_db(ai_results):
    """鎖死 A-T 欄同步映射 """
    try:
        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "client_name": st.session_state.client_name,
            "project_name": st.session_state.project_name,
            "event_date": f"{st.session_state.event_year} {st.session_state.event_month}",
            "venue": st.session_state.venue,
            "category_who": ", ".join(st.session_state.who_we_help),
            "category_what": ", ".join(st.session_state.what_we_do),
            "scope_of_work": ", ".join(st.session_state.scope_of_word),
            "youtube_link": st.session_state.youtube_link,
            "challenge": ai_results.get("website", {}).get("tc", {}).get("content", ""),
            "solution": ai_results.get("website", {}).get("tc", {}).get("content", ""),
            "ai_content": ai_results
        }
        res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=30)
        return res.status_code == 200
    except Exception as e:
        log_debug(f"Sync failed: {str(e)}", "error")
        return False

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    score_items = ["client_name", "project_name", "venue", "challenge", "solution", "youtube_link"]
    filled = sum([1 for f in score_items if st.session_state[f]])
    percent = int((filled / 12) * 100)

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    st.progress(filled/12, text=f"Progress: {percent}%")

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Content Generation & Sync"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Core Information")
        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.youtube_link = b3.text_input("YouTube Link", st.session_state.youtube_link)
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])
            if p := st.chat_input("匯報細節..."):
                st.session_state.messages.append({"role": "user", "content": p})
                res = call_gemini_sdk(f"User Data: {p}. Ask follow-up or generate if done.")
                st.session_state.messages.append({"role": "assistant", "content": res})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            files = st.file_uploader("Upload 4+ Photos", accept_multiple_files=True)
            if files: st.session_state.project_photos = files
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Platform Content Generation")
        
        # 讓用戶微調內容
        st.session_state.challenge = st.text_area("Boring Challenge (EN)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Creative Solution (EN)", st.session_state.solution)
        
        if st.button("🪄 一鍵生成餐廳專屬文案"):
            with st.spinner("🧠 正在根據輸入資料生成..."):
                # 🔥 鎖死數據注入，防止 AI 腦補城市規劃
                gen_prompt = f"""
                BASED ONLY ON THIS DATA:
                Client: {st.session_state.client_name}
                Project: {st.session_state.project_name}
                Challenge: {st.session_state.challenge}
                Solution: {st.session_state.solution}
                
                Task: Generate JSON for Slides, Socials, and Website (EN, TC, JP).
                Requirement: 50-100 words per section. No Simplified Chinese.
                """
                res_json = call_gemini_sdk(gen_prompt, is_json=True)
                if res_json:
                    st.session_state.ai_content = json.loads(res_json)
                    st.success("✅ 餐廳文案已生成！")

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync to Master DB"):
                if sync_to_master_db(st.session_state.ai_content):
                    st.balloons(); st.success("✅ 數據已成功同步至 Master DB A-T 欄！")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
