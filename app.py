import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import time
import json
import gspread
from datetime import datetime
from PIL import Image, ImageEnhance
from rembg import remove
from google.oauth2.service_account import Credentials

# --- 1. Firebean 核心配置 (符合 PDF 規範) ---
WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 2. 注入 PDF 精華的 AI 指令集 ---
FIREBEAN_SYSTEM_INSTRUCTION = """
You are 'Firebean Brain', the Architect of Public Engagement. Your identity is 'Institutional Cool'.
Follow these strict platform rules based on Firebean Style Guides:

1. GOOGLE SLIDE (EN ONLY): 
   - Structure: Hook (Provocative question) -> Shift (Interactive-Trust Framework) -> Proof (Success types).
   - Tone: Professional, punchy, business leader focus. No jargon.

2. LINKEDIN (EN ONLY): 
   - Structure: Bridge Structure (Boring Challenge -> Creative Translation -> Data Result). 
   - Tone: Grounded expert, institutional yet creative. Use bullet points for Key Takeaways.

3. FACEBOOK (Traditional Chinese): 
   - Tone: 'Weekend Planner' / 'Practical Parent' style. 
   - Strategy: Turn Policy into Play. Focus on storytelling and atmosphere.

4. IG & THREADS (Colloquial Cantonese + English): 
   - IG: 'Aesthetic First'. Use words like 'Vibe', 'Chill', '打卡世一'. 
   - Threads: 'Creative Insider'. Use unfilterted, fragmented sentences. 
   - Slang: 世一, Firm, 癲, 認真咩. Highlight the contrast between 'Boring Policy' and 'Cool Tech'.

5. WEBSITE (Trilingual: EN, TC, JP):
   - SEO/GEO Optimized. First 200 words rule. Professional yet engaging.
"""

# --- 3. 核心功能函數 ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", 
        "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "logo_white_b64": "", "logo_black_b64": "", "messages": [], 
        "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def manna_ai_enhance(image_file):
    img = Image.open(image_file)
    w, h = img.size
    with st.spinner("🚀 Manna AI Cinematic 處理中..."):
        time.sleep(0.8)
        # Cinematic 光效與擴展
        enhancer = ImageEnhance.Contrast(img); img = enhancer.enhance(1.3)
        if w < 1920:
            img = img.resize((1920, int(h * (1920 / w))), Image.Resampling.LANCZOS)
    return img, "✅ 已完成 Cinematic 擴展"

def sync_to_master_db(row):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gspread"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Firebean_Master_DB").worksheet("Basic Info")
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"GSheets Error: {e}")
        return False

# --- 4. 界面組件 ---
def get_circle_progress_html(percent):
    circumference = 439.8
    offset = circumference * (1 - percent/100)
    return f"""
    <div class="progress-container">
        <div class="neu-circle">
            <svg width="160" height="160">
                <circle stroke="#d1d9e6" stroke-width="12" fill="transparent" r="70" cx="80" cy="80"/>
                <circle stroke="#FF0000" stroke-width="12" stroke-dasharray="{circumference}" stroke-dashoffset="{offset}" 
                    stroke-linecap="round" fill="transparent" r="70" cx="80" cy="80" style="transition: all 0.8s;"/>
            </svg>
            <div class="pct-text">{percent}%</div>
        </div>
    </div>
    <style>
    .neu-circle {{ position: relative; width: 160px; height: 160px; background: #E0E5EC; border-radius: 50%; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center; }}
    .pct-text {{ position: absolute; font-size: 32px; font-weight: 900; color: #2D3436; }}
    </style>
    """

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.5); border-radius: 15px; }
        </style>
    """, unsafe_allow_html=True)

# --- 5. Main Loop ---
def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 進度計算
    score = sum([1 for f in ["client_name", "project_name", "venue", "challenge", "solution"] if st.session_state[f]])
    score += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.project_photos else 0)
    percent = int((score / 11) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=220)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Review & Marketing AI"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Project Basic Info")
        b1, b2, b3_y, b3_m, b4 = st.columns([1, 1, 0.6, 0.4, 1])
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("Year", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("Month", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.event_date = f"({st.session_state.event_year} {st.session_state.event_month})"
        st.session_state.venue = b4.text_input("Venue", st.session_state.venue)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        st.session_state.who_we_help = c1.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.session_state.what_we_do = c2.multiselect("🚀 What we do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean AI Chatbot")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            if p := st.chat_input("深挖呢個 Project 嘅 Cinematic Moment..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                model = genai.GenerativeModel("gemini-2.5-flash")
                res = model.generate_content(f"{FIREBEAN_SYSTEM_INSTRUCTION}\nContext: {st.session_state.scope_of_word}\nUser: {p}")
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Manna AI Gallery")
            files = st.file_uploader("Upload Photos", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                hero_choice = st.radio("Hero?", [f"P{i+1}" for i in range(len(files))], horizontal=True)
                st.session_state.hero_index = int(hero_choice[1:]) - 1
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        if st.button(f"✨ AI P{i+1}", key=f"ai_{i}"):
                            st.session_state.processed_photos[i], _ = manna_ai_enhance(f)
                        disp = st.session_state.processed_photos.get(i, Image.open(f))
                        border = "hero-border" if i == st.session_state.hero_index else ""
                        st.markdown(f'<div class="{border}">', unsafe_allow_html=True)
                        st.image(disp, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Five-Way Marketing AI")
        st.session_state.challenge = st.text_area("Challenge (EN)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution (EN)", st.session_state.solution)
        
        if st.button("🪄 一鍵生成五路營銷內容 (跟足 PDF 指南)"):
            with st.spinner("AI 正在根據 Firebean DNA 撰寫..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""
                {FIREBEAN_SYSTEM_INSTRUCTION}
                Generate content for: {st.session_state.project_name} at {st.session_state.venue}.
                Data: {st.session_state.challenge} / {st.session_state.solution}.
                Return a JSON with: slide_en, linkedin_en, facebook_ch, ig_threads_oral, web_en, web_ch, web_jp.
                """
                res = model.generate_content(prompt)
                st.session_state.ai_content = json.loads(res.text.replace("```json", "").replace("```", ""))
                st.success("✅ 所有平台文案已就緒！")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)

        if st.button("🚀 Confirm & Sync to Master DB"):
            c = st.session_state.ai_content
            row = [
                f"FB-{int(time.time())}", st.session_state.event_date, st.session_state.client_name, 
                st.session_state.project_name, st.session_state.venue, ", ".join(st.session_state.scope_of_word),
                ", ".join(st.session_state.who_we_help), ", ".join(st.session_state.what_we_do),
                "1", "", "", "Synced", "", "", "", "",
                st.session_state.project_name, st.session_state.challenge, st.session_state.solution, "",
                c['web_ch']['title'], c['web_ch']['challenge'], c['web_ch']['solution'], "",
                c['web_jp']['title'], c['web_jp']['challenge'], c['web_jp']['solution'], "",
                c.get('linkedin_en', ""), c.get('facebook_ch', ""), c.get('ig_threads_oral', ""), "", "", "", ""
            ]
            if sync_to_master_db(row):
                st.balloons(); st.success("✅ 數據已完美同步至 Firebean_Master_DB！")

if __name__ == "__main__": main()
