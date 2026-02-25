import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import time
import json
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from rembg import remove
from datetime import datetime

# --- 1. 定義環境 URL 與 選項清單 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwLR9MVr4rNgCQeXd2zGq43_F3ncsml_t7IP4OkjqBNtdNiv0ETitiuzx4oif3T0tCZ/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbya_pl6h99zY_LrURojCL86c20NwxdeW6V9bhCXqgPjJdz2NVPgeFThthcR6gfw0d1P/exec"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Follow 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
LinkedIn/Slides: EN only (Hook-Shift-Proof). IG/Threads: Canto-slang. Website: Trilingual (EN, TC, JP).
Motto: 'Turn Policy into Play'.
"""

# --- 2. 核心功能：Logo 與 影像處理 ---
def process_manna_logo(logo_file):
    with st.spinner("🎨 Manna AI 正在進行 Logo 提煉 (Vector-Look)..."):
        input_image = Image.open(logo_file)
        no_bg = remove(input_image, alpha_matting=True)
        alpha = no_bg.getchannel('A').filter(ImageFilter.GaussianBlur(radius=0.5))
        alpha = alpha.point(lambda p: 255 if p > 128 else 0)
        
        white_logo = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
        white_logo.putalpha(alpha)
        black_logo = Image.new("RGBA", no_bg.size, (0, 0, 0, 255))
        black_logo.putalpha(alpha)

        def to_b64(img):
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode()
        return to_b64(white_logo), to_b64(black_logo)

def manna_ai_enhance(image_file):
    img = Image.open(image_file)
    w, h = img.size
    with st.spinner("🚀 Manna AI Cinematic 處理中..."):
        img = ImageEnhance.Contrast(img).enhance(1.35)
        if w < 1920:
            new_h = int(h * (1920 / w))
            img = img.resize((1920, new_h), Image.Resampling.LANCZOS)
    return img

def sync_data(url, payload):
    try:
        response = requests.post(url, json=payload, timeout=40)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. UI 視覺樣式與進度環 ---
def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 5px solid #FF0000; box-shadow: 0 0 20px rgba(255,0,0,0.5); border-radius: 15px; }
        </style>
    """, unsafe_allow_html=True)

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 140px; height: 140px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="140" height="140"><circle stroke="#d1d9e6" stroke-width="10" fill="transparent" r="60" cx="70" cy="70"/><circle stroke="#FF0000" stroke-width="10" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="60" cx="70" cy="70" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg>
            <div style="position: absolute; font-size: 28px; font-weight: 900;">{percent}%</div>
        </div>
    </div>
    """

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "messages": [{"role": "assistant", "content": "Firebean Brain Online. Ready to Turn Policy into Play."}], 
        "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, "logo_white": "", "logo_black": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# --- 4. Main App 邏輯 ---
def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # --- 11 維度計分系統 (Progress %) ---
    filled = 0
    if st.session_state.client_name: filled += 1
    if st.session_state.project_name: filled += 1
    if st.session_state.venue: filled += 1
    if st.session_state.challenge: filled += 1
    if st.session_state.solution: filled += 1
    if st.session_state.who_we_help: filled += 1
    if st.session_state.what_we_do: filled += 1
    if st.session_state.scope_of_word: filled += 1
    if st.session_state.logo_white: filled += 1
    if st.session_state.project_photos: filled += 1
    if st.session_state.ai_content: filled += 1
    percent = int((filled / 11) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=220)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector & Chatbot", "📋 Ecosystem Sync & AI Content"])

    with tab1:
        # Logo 區
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Branding (Client Logo)")
        lc1, lc2 = st.columns([1, 2])
        with lc1:
            logo_in = st.file_uploader("Upload Logo", type=['png','jpg','jpeg'], key="logo_up")
            if logo_in and st.button("✨ Manna AI Refine"):
                st.session_state.logo_white, st.session_state.logo_black = process_manna_logo(logo_in)
        with lc2:
            if st.session_state.logo_white:
                sc1, sc2 = st.columns(2)
                sc1.image(f"data:image/png;base64,{st.session_state.logo_white}", caption="White (Slide)", width=100)
                sc2.image(f"data:image/png;base64,{st.session_state.logo_black}", caption="Black (Web)", width=100)
        st.markdown('</div>', unsafe_allow_html=True)

        # 基礎資訊區 (包含 What we do / SOW)
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Project Information")
        b1, b2, b3_y, b3_m, b4 = st.columns([1, 1, 0.6, 0.4, 1])
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("Year", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("Month", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.event_date = f"({st.session_state.event_year} {st.session_state.event_month})"
        st.session_state.venue = b4.text_input("Venue", st.session_state.venue)
        
        c1, c2, c3 = st.columns(3)
        st.session_state.who_we_help = c1.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.session_state.what_we_do = c2.multiselect("🚀 What we do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope of work", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        # AI Chatbot 區
        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean AI Chatbot")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            if p := st.chat_input("深挖呢個項目嘅 Interactive Soul..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                model = genai.GenerativeModel("gemini-2.5-flash")
                res = model.generate_content(f"{FIREBEAN_SYSTEM_PROMPT}\nSOW: {st.session_state.scope_of_word}\nUser: {p}")
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Manna Gallery")
            files = st.file_uploader("Upload 8 Photos", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                hero_choice = st.radio("🌟 Hero Banner?", [f"P{i+1}" for i in range(len(files))], horizontal=True)
                st.session_state.hero_index = int(hero_choice[1:]) - 1
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        if st.button(f"✨ AI P{i+1}", key=f"ai_{i}"):
                            st.session_state.processed_photos[i] = manna_ai_enhance(f)
                        img_disp = st.session_state.processed_photos.get(i, Image.open(f))
                        border = "hero-border" if i == st.session_state.hero_index else ""
                        st.markdown(f'<div class="{border}">', unsafe_allow_html=True)
                        st.image(img_disp, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Admin Review & Five-Way AI Sync")
        st.session_state.challenge = st.text_area("Challenge (EN Only for Slide)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution (EN Only for Slide)", st.session_state.solution)
        
        if st.button("🪄 一鍵生成五路文案 (Follow DNA)"):
            with st.spinner("AI 正在提煉策略與三語文案..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""
                {FIREBEAN_SYSTEM_PROMPT}
                Project: {st.session_state.project_name}. Challenge: {st.session_state.challenge}. Solution: {st.session_state.solution}.
                Generate JSON with keys: slide_en, linkedin_en, facebook_tc, ig_threads_oral, web_en, web_tc, web_jp.
                """
                res = model.generate_content(prompt)
                try:
                    st.session_state.ai_content = json.loads(res.text[res.text.find('{'):res.text.rfind('}')+1])
                    st.success("✅ 五路文案生成成功！")
                except: st.error("AI 格式解析失敗，請重試。")

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)

        if st.button("🚀 Confirm & Sync to Master Ecosystem"):
            b64_imgs = []
            for i in range(len(st.session_state.project_photos)):
                img = st.session_state.processed_photos.get(i, Image.open(st.session_state.project_photos[i]))
                buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); b64_imgs.append(base64.b64encode(buf.getvalue()).decode())
            
            payload = {
                "client_name": st.session_state.client_name, "project_name": st.session_state.project_name, "event_date": st.session_state.event_date,
                "venue": st.session_state.venue, "scope_of_work": ", ".join(st.session_state.scope_of_word),
                "category_who": ", ".join(st.session_state.who_we_help), "category_what": ", ".join(st.session_state.what_we_do),
                "challenge": st.session_state.challenge, "solution": st.session_state.solution,
                "ai": st.session_state.ai_content, "images": b64_imgs,
                "logo_white": st.session_state.logo_white, "logo_black": st.session_state.logo_black
            }
            
            res_sheet = sync_data(SHEET_SCRIPT_URL, payload)
            if "Success" in res_sheet:
                st.balloons(); st.success("✅ Master DB 同步成功！老細搞掂！")
            else: st.error(f"同步出錯: {res_sheet}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
