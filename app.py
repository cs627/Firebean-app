import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
from PIL import Image
from rembg import remove

# --- 1. 選項定義 (同步 Website) ---
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
        "project_photos": [], "hero_index": 0, "raw_logo": None
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！「大盒版」已就緒。請將所有資產直接掟入對應大盒，100% 成功感應！🥺"}]

# --- 3. 紅霓虹進度條 ---
def get_circle_progress_html(percent):
    circumference = 439.8
    offset = circumference * (1 - percent/100)
    return f"""
    <div class="header-right-container">
        <div class="neu-circle-bg">
            <svg width="160" height="160">
                <defs><filter id="neon-glow"><feGaussianBlur stdDeviation="3" result="cb"/><feMerge><feMergeNode in="cb"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
                <circle stroke="#d1d9e6" stroke-width="12" fill="transparent" r="70" cx="80" cy="80"/>
                <circle stroke="#FF0000" stroke-width="12" stroke-dasharray="{circumference}" stroke-dashoffset="{offset}" 
                    stroke-linecap="round" fill="transparent" r="70" cx="80" cy="80" filter="url(#neon-glow)" 
                    style="transition: stroke-dashoffset 0.8s; transform: rotate(-90deg); transform-origin: center;"/>
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
        .thumbnail-img { width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 12px; margin-top: 10px; }
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 10px rgba(255,0,0,0.5); }
        </style>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain 2.5", layout="wide")
    init_session_state()
    apply_styles()

    # --- ⚖️ 全方位計分系統 ---
    score = 0
    track = ["client_name", "project_name", "venue", "event_date", "challenge", "solution"]
    for f in track:
        if st.session_state[f]: score += 1
    if st.session_state.who_we_help: score += 1
    if st.session_state.what_we_do: score += 1
    if st.session_state.scope_of_word: score += 1
    if st.session_state.logo_white_b64: score += 1
    if st.session_state.project_photos: score += 1
    final_percent = int((score / 11) * 100)

    # --- 1. Header ---
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(final_percent), unsafe_allow_html=True)

    # --- 2. Logo Assets (大盒方案) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Assets Studio")
    f_logo = st.file_uploader("Drag logo here / Open file", type=['png','jpg','jpeg'], key="l_up")
    if f_logo: st.session_state.raw_logo = f_logo
    
    if st.session_state.raw_logo:
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            st.image(st.session_state.raw_logo, caption="Original", use_container_width=True)
            if st.button("🪄 Generate B&W Versions"):
                img = remove(Image.open(st.session_state.raw_logo))
                def colorize(img, color):
                    img = img.convert("RGBA")
                    a = img.split()[-1]
                    solid = Image.new('RGB', img.size, color)
                    final = Image.composite(solid, Image.new('RGB', img.size, (0,0,0)), a)
                    final.putalpha(a)
                    return final
                st.session_state.logo_white_b64 = base64.b64encode(io.BytesIO(colorize(img, (255,255,255)).tobytes()).getvalue()).decode()
                st.session_state.logo_black_b64 = base64.b64encode(io.BytesIO(colorize(img, (0,0,0)).tobytes()).getvalue()).decode()
                st.rerun()
        with col_l2:
            if st.session_state.logo_white_b64:
                st.markdown(f'<div style="background:#2D3436;border-radius:12px;padding:10px;"><img src="data:image/png;base64,{st.session_state.logo_white_b64}" style="width:100%;"></div>', unsafe_allow_html=True)
                st.caption("White Logo")
        with col_l3:
            if st.session_state.logo_black_b64:
                st.image(base64.b64decode(st.session_state.logo_black_b64), caption="Black Logo", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Review"])
    with tab1:
        # Basic Info
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Basic Information")
        b1, b2, b3_y, b3_m, b4 = st.columns([1, 1, 0.6, 0.4, 1])
        st.session_state.client_name = b1.text_input("客戶", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("項目", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("年", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("月", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.event_date = f"({st.session_state.event_year} {st.session_state.event_month})"
        st.session_state.venue = b4.text_input("地點", st.session_state.venue)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        st.session_state.who_we_help = c1.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.session_state.what_we_do = c2.multiselect("🚀 What we do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        col_l, col_r = st.columns([1.3, 1])
        with col_l:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            if p := st.chat_input("Talk to AI..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    res = model.generate_content(f"SOW:{st.session_state.scope_of_word}\nUser:{p}")
                    st.write(res.text); st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            # --- 4. Project Photos (大盒方案 + Hero 選擇) ---
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Photos")
            st.info("Drag 8 photos at least here / Open file")
            files = st.file_uploader("Upload Photos", type=['jpg','png','jpeg'], accept_multiple_files=True, key="p_up")
            if files: st.session_state.project_photos = files
            
            if st.session_state.project_photos:
                st.write("---")
                st.write("🌟 **Select Hero Banner (Preview Below):**")
                # 用 Radio 按鈕列出 1, 2, 3... 張相片供選擇
                hero_options = [f"Photo {i+1}" for i in range(len(st.session_state.project_photos))]
                choice = st.radio("哪一張是 Hero banner?", hero_options, index=st.session_state.hero_index, horizontal=True)
                st.session_state.hero_index = hero_options.index(choice)

                # 顯示縮圖
                cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with cols[i % 4]:
                        is_hero = (i == st.session_state.hero_index)
                        border = "hero-border" if is_hero else ""
                        st.markdown(f'<img src="data:image/png;base64,{base64.b64encode(f.getvalue()).decode()}" class="thumbnail-img {border}">', unsafe_allow_html=True)
                        if is_hero: st.caption("✅ HERO")
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
