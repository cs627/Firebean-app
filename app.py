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
# [cite_start]鎖死老細提供的新 GAS 同步 URL [cite: 1, 9-16]
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw5Bf3CsEYZJCEVzgzS_pSwg8y0B69iHLDywgZyz45ctsZTShe1YxRiTTKGjiMc1HFe/exec"

# 🔑 鎖死從 Streamlit Secrets 讀取 API Keys (解決 403 Leaked 問題)
API_KEYS_POOL = st.secrets.get("API_KEYS", [])

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# 鎖死核心 PR DNA
FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
Motto: 'Turn Policy into Play'. 
LinkedIn/Slides: Professional Business English. IG/Threads: Canto-slang. Website: Trilingual (EN, TC, JP).
Strictly NO Simplified Chinese. All Challenge/Solution sections must be 50-100 words.
"""

# --- 2. 核心 SDK 引擎與影像處理 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False, dynamic_sys_prompt=None):
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
        return base64.b64encode(buf.getvalue()).decode()
    except Exception: return ""

def manna_ai_enhance(image_file):
    with st.spinner("🚀 Manna AI 正在校正轉向並同步視角..."):
        try:
            raw_img = Image.open(image_file)
            img = ImageOps.exif_transpose(raw_img).convert("RGB")
            img_enhanced = ImageEnhance.Contrast(img).enhance(1.15)
            call_gemini_sdk("Analyze this photo.", image_file=img)
            return img_enhanced
        except Exception: return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

# --- 3. UI 視覺樣式與進度條 ---

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 25px; box-shadow: 12px 12px 24px #bec3c9, -12px -12px 24px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.4); border-radius: 12px; }
        .debug-terminal { background: #1E1E1E; color: #00FF00; padding: 12px; font-family: 'Courier New', monospace; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px 10px 0 0; max-height: 250px; overflow-y: auto; margin-top: 50px; }
        </style>
    """, unsafe_allow_html=True)

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""<div style="display: flex; justify-content: flex-end; align-items: center;"><div style="position: relative; width: 130px; height: 130px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;"><svg width="130" height="130"><circle stroke="#d1d9e6" stroke-width="10" fill="transparent" r="55" cx="65" cy="65"/><circle stroke="#FF0000" stroke-width="10" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="55" cx="65" cy="65" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg><div style="position: absolute; font-size: 26px; font-weight: 900; color: #2D3436;">{percent}%</div></div></div>"""

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "messages": [{"role": "assistant", "content": "Firebean Brain Online. 我係 PR Director。可唔可以講下今次項目 Client 遇到最大嘅 Challenge 係咩？"}],
        "project_photos": [], "hero_index": 0, "processed_photos": {}, "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": []
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def get_proactive_chatbot_prompt():
    """鎖定反問引導與資產提醒邏輯"""
    missing = [k for k in ["client_name", "project_name", "venue", "challenge", "solution", "youtube_link"] if not st.session_state.get(k)]
    return f"{FIREBEAN_SYSTEM_PROMPT}\nYou are a Proactive Senior PR Director. INTERVIEW user to gather: {missing}. Rules: 1. Probing questions. 2. Canto-slang. 3. Ask 1 thing at a time."

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 12 維度 Progress
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
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean Director (Interview)")
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])
            if p := st.chat_input("匯報細節..."):
                st.session_state.messages.append({"role": "user", "content": p})
                res = call_gemini_sdk(p, dynamic_sys_prompt=get_proactive_chatbot_prompt())
                st.session_state.messages.append({"role": "assistant", "content": res})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Require 4+ Photos)")
            files = st.file_uploader("Upload Photos", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                h_idx = min(st.session_state.hero_index, len(files)-1)
                hero_choice = st.radio("🌟 Highlight Hero Banner", [f"P{i+1}" for i in range(len(files))], index=h_idx, horizontal=True)
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
        st.header("📋 Platform Generation & Sync")
        st.session_state.challenge = st.text_area("Boring Challenge (EN)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Creative Solution (EN)", st.session_state.solution)
        
        if st.button("🪄 一鍵生成六大平台文案 (Follow DNA)"):
            with st.spinner("🧠 正在根據 PDF 萃取文案..."):
                prompt = "Generate Master JSON for Slides, Socials, and Website (Trilingual, 50-100 words)."
                res_json = call_gemini_sdk(prompt, is_json=True)
                if res_json: st.session_state.ai_content = json.loads(res_json); st.success("✅ 生成完畢！")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync to Master Ecosystem"):
                payload = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "client_name": st.session_state.client_name, "project_name": st.session_state.project_name, "ai_content": st.session_state.ai_content}
                res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=30)
                if res.status_code == 200: st.balloons(); st.success("✅ 同步 Master DB 成功！")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
