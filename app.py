import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import json
from PIL import Image
from rembg import remove

# --- 1. 選項與範圍定義 ---
WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

# 年份範圍：2015 - 2030
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 2. 系統初始化 ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", 
        "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "logo_white_b64": "", "logo_black_b64": "", "messages": [],
        "gallery_slots": [None] * 8
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！Hero Banner 預設為 Slot 1。請輸入資料及上傳相片，我會即時同步！🥺"}]

# --- 3. 紅霓虹泥膠進度條 (160px) ---
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
        
        /* 8 Slots 獨立樣式 */
        .slot-container { border-radius: 20px; padding: 10px; background: #E0E5EC; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; text-align: center; position: relative; min-height: 150px; }
        .hero-border { border: 4px solid #FF0000 !important; box-shadow: 0 0 20px #FF0000 !important; }
        .hero-label { position: absolute; top: -10px; left: 50%; transform: translateX(-50%); background: #FF0000; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold; z-index: 10; }
        .stFileUploader section { padding: 0 !important; }
        .stFileUploader label { display: none; }
        </style>
    """, unsafe_allow_html=True)

def colorize_logo(img, color):
    img = img.convert("RGBA")
    a = img.split()[-1]
    solid = Image.new('RGB', img.size, color)
    final = Image.composite(solid, Image.new('RGB', img.size, (0,0,0)), a)
    final.putalpha(a)
    return final

def main():
    st.set_page_config(page_title="Firebean Brain 2.5", layout="wide")
    init_session_state()
    apply_styles()

    # --- 1. Header (Logo & Neon Progress) ---
    col_h1, col_h2 = st.columns([1, 1])
    with col_h1:
        st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    
    # 進度計算 (9指標)
    track = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled = sum(1 for f in track if st.session_state[f])
    percent = int(((filled + (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0) + (1 if any(st.session_state.gallery_slots) else 0)) / 9) * 100)
    with col_h2:
        st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    # --- 2. Logo Studio (置頂) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Studio")
    l1, l2 = st.columns([1, 2])
    with l1:
        logo_f = st.file_uploader("Upload Logo", type=['png','jpg','jpeg'], key="l_up")
        if st.button("🪄 一鍵生成雙色") and logo_f:
            img = remove(Image.open(logo_f))
            st.session_state.logo_white_b64 = base64.b64encode(io.BytesIO(colorize_logo(img, (255,255,255)).tobytes()).getvalue()).decode()
            st.session_state.logo_black_b64 = base64.b64encode(io.BytesIO(colorize_logo(img, (0,0,0)).tobytes()).getvalue()).decode()
            st.rerun()
    with l2:
        if st.session_state.logo_white_b64: st.success("✅ 雙色 Logo 已同步")
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Dashboard"])

    with tab1:
        # --- 3. Basic Info (年份 2015-2030) ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Basic Information")
        b1, b2, b3_y, b3_m, b4 = st.columns([1, 1, 0.6, 0.4, 1])
        st.session_state.client_name = b1.text_input("客戶名稱", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("項目名稱", st.session_state.project_name)
        
        
        
        st.session_state.event_year = b3_y.selectbox("年份", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("月份", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.event_date = f"({st.session_state.event_year} {st.session_state.event_month})"
        st.session_state.venue = b4.text_input("地點", st.session_state.venue)
        st.markdown('</div>', unsafe_allow_html=True)

        # --- 4. 三大 Checkbox ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        st.session_state.who_we_help = c1.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.session_state.what_we_do = c2.multiselect("🚀 What we do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope_of_Word", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        col_left, col_right = st.columns([1.3, 1])
        with col_left:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI Deep Inquiry")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            if p := st.chat_input("話我知個 Project 邊度最難搞？"):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    res = model.generate_content(f"SOW:{st.session_state.scope_of_word}, Client:{st.session_state.client_name}\nUser:{p}")
                    st.write(res.text); st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_right:
            # --- 5. 8 Slot 獨立拖放 (Slot 1 為 Hero) ---
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery (Slot 1 = Hero Banner)")
            for row in range(2):
                cols = st.columns(4)
                for c_idx in range(4):
                    slot_idx = row * 4 + c_idx
                    with cols[c_idx]:
                        # Slot 1 預設 Hero 效果
                        is_hero = (slot_idx == 0)
                        hero_class = "hero-border" if is_hero else ""
                        st.markdown(f'<div class="slot-container {hero_class}">', unsafe_allow_html=True)
                        if is_hero: st.markdown('<div class="hero-label">HERO</div>', unsafe_allow_html=True)
                        
                        if st.session_state.gallery_slots[slot_idx]:
                            st.image(Image.open(st.session_state.gallery_slots[slot_idx]), use_column_width=True)
                        
                        f = st.file_uploader(f"S{slot_idx+1}", type=['jpg','png','jpeg'], key=f"s_{slot_idx}")
                        if f: st.session_state.gallery_slots[slot_idx] = f
                        st.markdown(f'Slot {slot_idx+1}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Admin Review (Real-time Sync)")
        st.write(f"**Client:** {st.session_state.client_name} | **Date:** {st.session_state.event_date}")
        st.session_state.challenge = st.text_area("Final Challenge", st.session_state.challenge)
        st.session_state.solution = st.text_area("Final Innovation", st.session_state.solution)
        if st.button("🚀 Confirm & Submit"):
            st.balloons(); st.success("✅ 資料同步成功！Hero Banner 已鎖定於 Slot 1。")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
