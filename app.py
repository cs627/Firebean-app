import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import time
import gspread
from datetime import datetime
from PIL import Image, ImageEnhance
from rembg import remove
from google.oauth2.service_account import Credentials

# --- 1. 配置與清單 ---
WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 2. 系統初始化 ---
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
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！Master DB 與社交媒體 AI 已就緒。請上傳資料！🥺"}]

# --- 3. Google Sheets 同步引擎 ---
def sync_to_master_db(row_data):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # 確保你在 Streamlit Cloud Secrets 設定了 gspread 欄位
        creds = Credentials.from_service_account_info(st.secrets["gspread"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Firebean_Master_DB").worksheet("Basic Info")
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"GSheets Sync Error: {e}. 記得檢查 Secrets 同 Sheet Sharing 權限！")
        return False

# --- 4. Manna AI 影像引擎 ---
def manna_ai_enhance(image_file):
    img = Image.open(image_file)
    w, h = img.size
    with st.spinner("🚀 Manna AI Cinematic 處理中..."):
        time.sleep(1)
        # Cinematic 調色
        enhancer = ImageEnhance.Contrast(img); img = enhancer.enhance(1.25)
        # 自動 Extend 像素
        if w < 1920:
            img = img.resize((1920, int(h * (1920 / w))), Image.Resampling.LANCZOS)
    return img, "✅ Cinematic Enhanced (1920px)"

# --- 5. UI 視覺 (Neon Progress) ---
def get_circle_progress_html(percent):
    circumference = 439.8
    offset = circumference * (1 - percent/100)
    return f"""
    <div class="header-right-container">
        <div class="neu-circle-bg">
            <svg width="160" height="160">
                <defs><filter id="neon-glow"><feGaussianBlur stdDeviation="3" result="cb"/><feMerge><feMergeNode in="cb"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
                <circle stroke="#d1d9e6" stroke-width="12" fill="transparent" r="70" cx="80" cy="80"/>
                <circle stroke="#FF0000" stroke-width="12" stroke-dasharray="{circumference}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="70" cx="80" cy="80" filter="url(#neon-glow)" style="transition: stroke-dashoffset 0.8s; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div class="progress-text">{percent}<span style="font-size:16px;">%</span></div>
        </div>
    </div>
    <style>
    .header-right-container {{ display: flex; justify-content: flex-end; align-items: center; }}
    .neu-circle-bg {{ position: relative; width: 160px; height: 160px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center; }}
    .progress-text {{ position: absolute; font-size: 38px; font-weight: 900; color: #2D3436; font-family: 'Arial Black'; }}
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

def main():
    st.set_page_config(page_title="Firebean Brain 2.5", layout="wide")
    init_session_state()
    apply_styles()

    # 進度計算
    score = sum([1 for f in ["client_name", "project_name", "venue", "challenge", "solution"] if st.session_state[f]])
    if st.session_state.who_we_help: score += 1
    if st.session_state.what_we_do: score += 1
    if st.session_state.scope_of_word: score += 1
    if st.session_state.logo_white_b64: score += 1
    if st.session_state.project_photos: score += 1
    if st.session_state.ai_content: score += 1
    final_percent = int((score / 11) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(final_percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Collector & Manna AI", "📋 Admin Review & Sync"])

    with tab1:
        # Basic Info
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Basic Information")
        b1, b2, b3_y, b3_m, b4 = st.columns([1, 1, 0.6, 0.4, 1])
        st.session_state.client_name = b1.text_input("客戶", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("項目名稱", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("年份", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("月份", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.event_date = f"({st.session_state.event_year} {st.session_state.event_month})"
        st.session_state.venue = b4.text_input("地點", st.session_state.venue)
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
            if p := st.chat_input("話我知個 Project 邊度最難搞？"):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    # 注入 NotebookLM Guideline
                    sys_prompt = f"你係 Firebean Brain。請根據 SOW: {st.session_state.scope_of_word} 進行深挖，確保符合 Cinematic Style。"
                    res = model.generate_content(f"{sys_prompt}\nUser: {p}")
                    st.write(res.text); st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Manna AI Gallery")
            files = st.file_uploader("Upload 8 Photos", type=['jpg','png','jpeg'], accept_multiple_files=True)
            if files: 
                st.session_state.project_photos = files
                hero_options = [f"Photo {i+1}" for i in range(len(files))]
                choice = st.radio("🌟 Select Hero", hero_options, index=st.session_state.hero_index, horizontal=True)
                st.session_state.hero_index = hero_options.index(choice)
                
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        if st.button(f"✨ AI P{i+1}", key=f"ai_{i}"):
                            st.session_state.processed_photos[i], _ = manna_ai_enhance(f)
                        is_hero = (i == st.session_state.hero_index)
                        border = "hero-border" if is_hero else ""
                        img_disp = st.session_state.processed_photos.get(i, Image.open(f))
                        st.markdown(f'<div class="{border}">', unsafe_allow_html=True)
                        st.image(img_disp, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Admin & Marketing Sync")
        st.session_state.challenge = st.text_area("Challenge (EN)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution (EN)", st.session_state.solution)
        
        if st.button("🪄 生成三語及社群內容 (Follow Firebean Guideline)"):
            with st.spinner("AI 撰寫中..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"根據資料生成 Firebean Master DB 內容 (LinkedIn, FB, IG, 三語): {st.session_state.project_name}, {st.session_state.challenge}, {st.session_state.solution}"
                res = model.generate_content(prompt)
                # 簡單模擬 JSON 提取 (實際可用 JSON 解析)
                st.session_state.ai_content = {"draft": res.text}
                st.success("✅ AI 內容已生成！")
        
        if st.session_state.ai_content:
            st.write(st.session_state.ai_content["draft"])

        if st.button("🚀 Confirm & Sync to Master DB"):
            row = [
                f"FB-{int(time.time())}", 
                st.session_state.event_date,
                st.session_state.client_name,
                st.session_state.project_name,
                st.session_state.venue,
                ", ".join(st.session_state.scope_of_word),
                ", ".join(st.session_state.who_we_help),
                ", ".join(st.session_state.what_we_do),
                "1", "", "", "Synced", "", "", "", "", 
                st.session_state.project_name, 
                st.session_state.challenge, 
                st.session_state.solution,
                "", "", "", "", "", "", "", "", "", # 補足 DB 欄位
                st.session_state.ai_content.get("draft", "")
            ]
            if sync_to_master_db(row):
                st.balloons(); st.success("✅ 已同步至 Firebean_Master_DB！")

if __name__ == "__main__": main()
