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

# --- 1. 配置與 Firebean DNA 清單 ---
WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 2. 注入 PDF 精華的終極系統指令 (The Architect of Public Engagement) ---
FIREBEAN_SYSTEM_INSTRUCTION = """
You are 'Firebean Brain', the Architect of Public Engagement. Your identity is 'Institutional Cool'—fusing Government Authority with Lifestyle Creativity.
Motto: 'Turn Policy into Play' and 'Create to Engage'.

Strategic Logic: Use the 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).

Platform-Specific Rules:
1. GOOGLE SLIDE (EN ONLY): Professional, follow 'Hook-Shift-Proof' structure. Bullet points for results.
2. LINKEDIN (EN ONLY): 'Institutional Cool' tone. Professional insight pivoting to interactive soul. Use 'Bridge Structure'.
3. FACEBOOK (TC): 'Weekend Planner' / 'Practical Parent' style. Focus on storytelling, detailed activities, and parent-child interaction.
4. IG & THREADS (Colloquial Canto-English): 'Aesthetic First'. Use slang (世一, Firm, Vibe, 癲). Focus on 'Contrast Flex' (boring topic vs. cool tech).
5. WEBSITE (Trilingual: EN, TC, JP): SEO/GEO optimized. First 200 words rule. Professional but energetic.
"""

# --- 3. 核心功能 ---
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
        time.sleep(1)
        # Cinematic 調色
        enhancer = ImageEnhance.Contrast(img); img = enhancer.enhance(1.3)
        enhancer = ImageEnhance.Color(img); img = enhancer.enhance(1.1)
        # 模擬 Generative Resize (等比放大至 1920)
        if w < 1920:
            img = img.resize((1920, int(h * (1920 / w))), Image.Resampling.LANCZOS)
    return img, "✅ Cinematic Processed"

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

# --- 4. UI 視覺樣式 (Neumorphism + Neon) ---
def get_circle_progress_html(percent):
    circumference = 439.8
    offset = circumference * (1 - percent/100)
    return f"""
    <div class="header-right-container">
        <div class="neu-circle-bg">
            <svg width="160" height="160">
                <circle stroke="#d1d9e6" stroke-width="12" fill="transparent" r="70" cx="80" cy="80"/>
                <circle stroke="#FF0000" stroke-width="12" stroke-dasharray="{circumference}" stroke-dashoffset="{offset}" 
                    stroke-linecap="round" fill="transparent" r="70" cx="80" cy="80" style="transition: stroke-dashoffset 0.8s; transform: rotate(-90deg); transform-origin: center; filter: drop-shadow(0 0 5px #FF0000);"/>
            </svg>
            <div class="progress-text">{percent}%</div>
        </div>
    </div>
    <style>
    .header-right-container {{ display: flex; justify-content: flex-end; align-items: center; }}
    .neu-circle-bg {{ position: relative; width: 160px; height: 160px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center; }}
    .progress-text {{ position: absolute; font-size: 38px; font-weight: 900; color: #2D3436; }}
    </style>
    """

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 5px solid #FF0000; box-shadow: 0 0 20px rgba(255,0,0,0.5); border-radius: 15px; }
        </style>
    """, unsafe_allow_html=True)

# --- 5. Main App ---
def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 計分系統 (11 維度)
    score = sum([1 for f in ["client_name", "project_name", "venue", "challenge", "solution"] if st.session_state[f]])
    score += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    score += (1 if st.session_state.project_photos else 0) + (1 if st.session_state.ai_content else 0)
    final_percent = int((score / 11) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=220)
    with c2: st.markdown(get_circle_progress_html(final_percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector & Manna AI", "📋 Admin Review & 五路分流 AI"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Project Basic Information")
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
            st.subheader("🤖 AI Chatbot (Deep Inquiry)")
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
            files = st.file_uploader("Upload Photos (Drag & Drop)", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                hero_choice = st.radio("🌟 Select Hero Banner", [f"P{i+1}" for i in range(len(files))], horizontal=True)
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
        st.header("📋 Five-Way Marketing AI & Master DB Sync")
        st.session_state.challenge = st.text_area("Challenge (EN Only for Slides)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution (EN Only for Slides)", st.session_state.solution)
        
        if st.button("🪄 一鍵生成五路營銷內容 (跟足 PDF 與 NotebookLM 指引)"):
            with st.spinner("AI 正在進行策略提煉..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""
                {FIREBEAN_SYSTEM_INSTRUCTION}
                Generate marketing assets for: {st.session_state.project_name} at {st.session_state.venue}.
                Project Challenge: {st.session_state.challenge}
                Project Solution: {st.session_state.solution}

                Output JSON:
                {{
                    "slide_en": {{"hook": "...", "shift": "...", "proof": "..."}},
                    "linkedin_en": "Professional Bridge Structure",
                    "facebook_tc": "Detailed storytelling, parent-friendly",
                    "ig_threads_oral": "Colloquial Canto-English, 世一 vibe",
                    "web_en": {{"title": "...", "challenge": "...", "solution": "..."}},
                    "web_tc": {{"title": "...", "challenge": "...", "solution": "..."}},
                    "web_jp": {{"title": "...", "challenge": "...", "solution": "..."}}
                }}
                """
                res = model.generate_content(prompt)
                st.session_state.ai_content = json.loads(res.text.replace("```json", "").replace("```", ""))
                st.success("✅ 五路分流營銷文案已備妥！")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)

        if st.button("🚀 Confirm & Sync to Firebean_Master_DB"):
            c = st.session_state.ai_content
            # 填寫 36 個欄位的 Row (根據 Firebean_Master_DB PDF 結構)
            row = [
                f"FB-{int(time.time())}", st.session_state.event_date, st.session_state.client_name, 
                st.session_state.project_name, st.session_state.venue, ", ".join(st.session_state.scope_of_word),
                ", ".join(st.session_state.who_we_help), ", ".join(st.session_state.what_we_do),
                "1", "Chatbot Summary", "", "Synced", "", "", "", "", # 欄位 9-16
                st.session_state.project_name, # Title_EN (17)
                st.session_state.challenge, # Challenge_EN (18)
                st.session_state.solution, # Solution_EN (19)
                "", # Result_EN (20)
                c['web_tc']['title'], c['web_tc']['challenge'], c['web_tc']['solution'], "", # 21-24
                c['web_jp']['title'], c['web_jp']['challenge'], c['web_jp']['solution'], "", # 25-28
                c.get('linkedin_en', ""), c.get('facebook_tc', ""), c.get('ig_threads_oral', ""), # 29-31
                "", "", "Generated", "TRUE", "" # 32-36
            ]
            if sync_to_master_db(row):
                st.balloons(); st.success("✅ 資料已同步至 Master DB！")

if __name__ == "__main__": main()
