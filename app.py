import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import time
import json
from PIL import Image, ImageEnhance
from datetime import datetime

# --- 1. 配置與 Firebean DNA 清單 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwLR9MVr4rNgCQeXd2zGq43_F3ncsml_t7IP4OkjqBNtdNiv0ETitiuzx4oif3T0tCZ/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbya_pl6h99zY_LrURojCL86c20NwxdeW6V9bhCXqgPjJdz2NVPgeFThthcR6gfw0d1P/exec"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 2. 注入 5 份 PDF 靈魂的系統指令 ---
FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Your voice is 'Institutional Cool'—fusing Government Authority with Lifestyle Creativity.
Motto: 'Turn Policy into Play' and 'Create to Engage'.

Platform Content Strategy:
1. GOOGLE SLIDE (EN ONLY): Follow 'Hook-Shift-Proof' structure. Professional, punchy business leader focus.
2. LINKEDIN (EN ONLY): 'Institutional Cool' tone. Follow 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
3. FACEBOOK (Traditional Chinese): 'Weekend Planner' style. Detailed storytelling, parent-friendly.
4. IG & THREADS (Colloquial Canto-English): 'Aesthetic First'. Use slang (世一, Firm, Vibe, 癲). Focus on 'Contrast Flex'.
5. WEBSITE (Trilingual): EN, TC, and JP. SEO/GEO optimized. First 200 words rule.
"""

# --- 3. 核心功能函數 ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", 
        "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "messages": [], "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def manna_ai_enhance(image_file):
    img = Image.open(image_file)
    w, h = img.size
    with st.spinner("🚀 Manna AI Cinematic 處理中..."):
        time.sleep(0.8)
        # Cinematic Color & Contrast
        img = ImageEnhance.Contrast(img).enhance(1.35)
        img = ImageEnhance.Color(img).enhance(1.15)
        # Generative Resize to 1920px width if small
        if w < 1920:
            new_h = int(h * (1920 / w))
            img = img.resize((1920, new_h), Image.Resampling.LANCZOS)
    return img

def sync_data(url, payload):
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- 4. UI 視覺樣式 (Neumorphism) ---
def get_circle_progress_html(percent):
    circumference = 439.8
    offset = circumference * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 160px; height: 160px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="160" height="160">
                <circle stroke="#d1d9e6" stroke-width="12" fill="transparent" r="70" cx="80" cy="80"/>
                <circle stroke="#FF0000" stroke-width="12" stroke-dasharray="{circumference}" stroke-dashoffset="{offset}" 
                    stroke-linecap="round" fill="transparent" r="70" cx="80" cy="80" style="transition: stroke-dashoffset 0.8s; transform: rotate(-90deg); transform-origin: center; filter: drop-shadow(0 0 5px #FF0000);"/>
            </svg>
            <div style="position: absolute; font-size: 32px; font-weight: 900; color: #2D3436;">{percent}%</div>
        </div>
    </div>
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

# --- 5. Main Loop ---
def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 進度計算 (11維度)
    score = sum([1 for f in ["client_name", "project_name", "venue", "challenge", "solution"] if st.session_state[f]])
    score += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    score += (1 if st.session_state.project_photos else 0) + (1 if st.session_state.ai_content else 0)
    percent = int((score / 11) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=220)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Review & Ecosystem Sync"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Basic Information")
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
            if p := st.chat_input("深挖呢個項目嘅 Interactive Soul..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                model = genai.GenerativeModel("gemini-2.5-flash")
                res = model.generate_content(f"{FIREBEAN_SYSTEM_PROMPT}\nContext: {st.session_state.scope_of_word}\nUser: {p}")
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Manna AI Gallery")
            files = st.file_uploader("Upload 8 Photos", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                hero_choice = st.radio("Select Hero", [f"P{i+1}" for i in range(len(files))], horizontal=True)
                st.session_state.hero_index = int(hero_choice[1:]) - 1
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        if st.button(f"✨ AI P{i+1}", key=f"ai_{i}"):
                            st.session_state.processed_photos[i] = manna_ai_enhance(f)
                        border = "hero-border" if i == st.session_state.hero_index else ""
                        img_disp = st.session_state.processed_photos.get(i, Image.open(f))
                        st.markdown(f'<div class="{border}">', unsafe_allow_html=True)
                        st.image(img_disp, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Admin Review & Ecosystem Sync")
        st.session_state.challenge = st.text_area("Challenge (EN Only for Slide)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution (EN Only for Slide)", st.session_state.solution)
        
        if st.button("🪄 一鍵生成五路營銷內容 (Follow DNA Guides)"):
            with st.spinner("AI 正在提煉策略與三語文案..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""
                {FIREBEAN_SYSTEM_PROMPT}
                Project: {st.session_state.project_name}. Challenge: {st.session_state.challenge}. Solution: {st.session_state.solution}.
                Generate JSON: slide_en (hook, shift, proof), linkedin_en, facebook_tc, ig_threads_oral, web_en/tc/jp (title, challenge, solution).
                """
                res = model.generate_content(prompt)
                st.session_state.ai_content = json.loads(res.text.replace("```json", "").replace("```", ""))
                st.success("✅ 文案已生成！")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)

        if st.button("🚀 Confirm & Sync to Firebean Ecosystem"):
            # 準備相片 Base64
            b64_images = []
            for i in range(len(st.session_state.project_photos)):
                img = st.session_state.processed_photos.get(i, Image.open(st.session_state.project_photos[i]))
                buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85)
                b64_images.append(base64.b64encode(buf.getvalue()).decode())

            # 構建 Payload
            payload = {
                "client_name": st.session_state.client_name,
                "project_name": st.session_state.project_name,
                "event_date": st.session_state.event_date,
                "venue": st.session_state.venue,
                "scope_of_work": ", ".join(st.session_state.scope_of_word),
                "category_who": ", ".join(st.session_state.who_we_help),
                "category_what": ", ".join(st.session_state.what_we_do),
                "challenge": st.session_state.challenge,
                "solution": st.session_state.solution,
                "ai": st.session_state.ai_content,
                "images": b64_images
            }

            # 同步到 Sheet (36 欄位)
            res_sheet = sync_data(SHEET_SCRIPT_URL, payload)
            # 同步到 Slide
            res_slide = sync_data(SLIDE_SCRIPT_URL, payload)
            
            if "Success" in res_sheet or "success" in res_slide:
                st.balloons()
                st.success(f"✅ Master DB 及 Slide 同步成功！")
            else:
                st.error(f"同步出錯: Sheet({res_sheet}) | Slide({res_slide})")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
