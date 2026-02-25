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

# --- 1. 配置與 URL ---
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
LinkedIn/Slides: EN only (Hook-Shift-Proof). IG/Threads: Canto-slang. Website: Trilingual.
"""

# --- 2. 核心功能：Logo 與 影像處理 ---
def process_manna_logo(logo_file):
    """將上傳的 Logo 去背景並生成黑、白兩色高對比版本"""
    with st.spinner("🎨 Manna AI 正在進行 Logo 提煉 (Vector-Look)..."):
        input_image = Image.open(logo_file)
        # AI 去背景
        no_bg = remove(input_image, alpha_matting=True)
        # 處理透明層
        alpha = no_bg.getchannel('A').filter(ImageFilter.GaussianBlur(radius=0.5))
        alpha = alpha.point(lambda p: 255 if p > 128 else 0)
        
        # 生成透明底純白 Logo
        white_logo = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
        white_logo.putalpha(alpha)
        
        # 生成透明底純黑 Logo (修正了括號閉合問題)
        black_logo = Image.new("RGBA", no_bg.size, (0, 0, 0, 255))
        black_logo.putalpha(alpha)

        def to_b64(img):
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode()
            
        return to_b64(white_logo), to_b64(black_logo)

def manna_ai_enhance(image_file):
    """影像處理：增加電影感對比度並自動 Resize"""
    img = Image.open(image_file)
    w, h = img.size
    with st.spinner("🚀 Manna AI Cinematic 處理中..."):
        img = ImageEnhance.Contrast(img).enhance(1.35)
        if w < 1920:
            new_h = int(h * (1920 / w))
            img = img.resize((1920, new_h), Image.Resampling.LANCZOS)
    return img

def sync_data(url, payload):
    """對接 Google Apps Script"""
    try:
        response = requests.post(url, json=payload, timeout=40)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. UI 視覺樣式與初始化 ---
def apply_styles():
    """定義 Neumorphism 風格 CSS"""
    st.markdown("""
        <style>
        header {visibility: hidden;} 
        footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 5px solid #FF0000; box-shadow: 0 0 20px rgba(255,0,0,0.5); border-radius: 15px; }
        </style>
    """, unsafe_allow_html=True)

def get_circle_progress_html(percent):
    """能量環 HTML"""
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 140px; height: 140px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="140" height="140">
                <circle stroke="#d1d9e6" stroke-width="10" fill="transparent" r="60" cx="70" cy="70"/>
                <circle stroke="#FF0000" stroke-width="10" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" 
                    stroke-linecap="round" fill="transparent" r="60" cx="70" cy="70" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position: absolute; font-size: 28px; font-weight: 900; color: #2D3436;">{percent}%</div>
        </div>
    </div>
    """

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", 
        "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "messages": [], "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, "logo_white": "", "logo_black": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# --- 4. Main Loop ---
def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 計分
    score = sum([1 for f in ["client_name", "project_name", "venue", "challenge", "solution"] if st.session_state[f]])
    score += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.project_photos else 0)
    score += (1 if st.session_state.logo_white else 0) + (1 if st.session_state.ai_content else 0)
    percent = int((score / 10) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=200)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector & Branding", "📋 Ecosystem Sync & AI"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Client Branding Assets")
        lc1, lc2 = st.columns([1, 2])
        with lc1:
            logo_in = st.file_uploader("Upload Client Logo", type=['png','jpg','jpeg'], key="logo_up")
            if logo_in:
                if st.button("✨ Manna AI Refine Logo"):
                    st.session_state.logo_white, st.session_state.logo_black = process_manna_logo(logo_in)
        with lc2:
            if st.session_state.logo_white:
                sc1, sc2 = st.columns(2)
                sc1.image(f"data:image/png;base64,{st.session_state.logo_white}", caption="White (for Slides)", width=100)
                sc2.image(f"data:image/png;base64,{st.session_state.logo_black}", caption="Black (for Web)", width=100)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Project Basic Information")
        b1, b2, b3_y, b3_m, b4 = st.columns([1, 1, 0.6, 0.4, 1])
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project Name", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("Year", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("Month", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.event_date = f"({st.session_state.event_year} {st.session_state.event_month})"
        st.session_state.venue = b4.text_input("Venue", st.session_state.venue)
        st.session_state.who_we_help = st.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📸 Manna AI Gallery")
        files = st.file_uploader("Upload 8 Project Photos", accept_multiple_files=True)
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
        st.header("📋 Admin Review & Ecosystem Sync")
        st.session_state.challenge = st.text_area("Challenge (EN Only for Slide)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution (EN Only for Slide)", st.session_state.solution)
        
        if st.button("🪄 一鍵生成五路營銷文案 (Refined AI)"):
            with st.spinner("AI 正在提煉策略與三語文案..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""
                {FIREBEAN_SYSTEM_PROMPT}
                Project: {st.session_state.project_name}. Challenge: {st.session_state.challenge}. Solution: {st.session_state.solution}.
                Output JSON with: slide_en, linkedin_en, facebook_tc, ig_threads_oral, web_en, web_tc, web_jp.
                """
                res = model.generate_content(prompt)
                try:
                    st.session_state.ai_content = json.loads(res.text.replace("```json", "").replace("```", ""))
                    st.success("✅ 五路文案生成成功！")
                except:
                    st.error("AI 格式錯誤，請重試一次。")

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)

        if st.button("🚀 Confirm & Sync to Master DB"):
            b64_imgs = []
            for i in range(len(st.session_state.project_photos)):
                img = st.session_state.processed_photos.get(i, Image.open(st.session_state.project_photos[i]))
                buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85)
                b64_imgs.append(base64.b64encode(buf.getvalue()).decode())
            
            payload = {
                "client_name": st.session_state.client_name,
                "project_name": st.session_state.project_name,
                "event_date": st.session_state.event_date,
                "venue": st.session_state.venue,
                "challenge": st.session_state.challenge,
                "solution": st.session_state.solution,
                "ai": st.session_state.ai_content,
                "images": b64_imgs,
                "logo_white": st.session_state.logo_white,
                "logo_black": st.session_state.logo_black
            }
            
            with st.spinner("同步數據中..."):
                res_sheet = sync_data(SHEET_SCRIPT_URL, payload)
                if "Success" in res_sheet:
                    st.balloons(); st.success("✅ Master DB 同步成功！老細搞掂！")
                else:
                    st.error(f"同步出錯: {res_sheet}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
