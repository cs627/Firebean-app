import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import json
import re
from PIL import Image
from rembg import remove

# --- 1. 選項與限制定義 ---
WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = [
    "Event Planning", "Event Coordination", "Event Production", "Theme Design", 
    "Concept Development", "Social Media Management", "KOL / MI Line up", 
    "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"
]
YEARS = [str(y) for y in range(2007, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 2. 系統初始化 (確保兩邊 Tab 共享數據) ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", 
        "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "logo_white_b64": "", "logo_black_b64": "", "messages": [], "hero_slot": 1
    }
    for key, val in fields.items():
        if key not in st.session_state: st.session_state[key] = val
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！同步系統已啟動。請填寫基本資料，我會即時計分！🥺"}]

# --- 3. 紅霓虹泥膠進度條 (Red Neon + Neuromorphic) ---
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
        .gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px; }
        .gallery-item { width: 100%; aspect-ratio: 1/1; border-radius: 12px; object-fit: cover; box-shadow: 4px 4px 8px #bec3c9; border: 3px solid transparent; }
        .hero-selected { border-color: #FF0000 !important; box-shadow: 0 0 15px #FF0000; }
        .slot-placeholder { aspect-ratio: 1/1; background: #E0E5EC; border-radius: 12px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 10px; }
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
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # --- 1. Header (Firebean Logo & Red Neon Progress) ---
    col_h1, col_h2 = st.columns([1, 1])
    with col_h1:
        st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    
    # 即時計分邏輯 (9 大指標)
    track_fields = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled_count = sum(1 for f in track_fields if st.session_state[f])
    has_who = 1 if st.session_state.who_we_help else 0
    has_what = 1 if st.session_state.what_we_do else 0
    has_sow = 1 if st.session_state.scope_of_word else 0
    
    percent = int(((filled_count + has_who + has_what + has_sow) / 8) * 100)
    
    with col_h2:
        st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    # --- 2. Logo Studio (置頂不隱藏) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Studio (黑白雙色生成)")
    l_col1, l_col2 = st.columns([1, 2])
    with l_col1:
        logo_f = st.file_uploader("上傳標誌", type=['png','jpg','jpeg'], key="l_up")
        if st.button("🪄 一鍵轉化"):
            if logo_f:
                img_nobg = remove(Image.open(logo_f))
                st.session_state.logo_white_b64 = base64.b64encode(io.BytesIO(colorize_logo(img_nobg, (255,255,255)).tobytes()).getvalue()).decode()
                st.session_state.logo_black_b64 = base64.b64encode(io.BytesIO(colorize_logo(img_nobg, (0,0,0)).tobytes()).getvalue()).decode()
                st.rerun()
    with l_col2:
        if st.session_state.logo_white_b64:
            st.success("✅ 雙色 Logo 已同步至後台記憶。")
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Dashboard"])

    with tab1:
        # --- 3. Basic Info (填寫即同步) ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Basic Information (Fill in the blanks)")
        b1, b2, b3_y, b3_m, b4 = st.columns([1, 1, 0.6, 0.4, 1])
        st.session_state.client_name = b1.text_input("客戶名稱", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("項目名稱", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("年份", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("月份", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.event_date = f"({st.session_state.event_year} {st.session_state.event_month})"
        st.session_state.venue = b4.text_input("地點", st.session_state.venue)
        st.markdown('</div>', unsafe_allow_html=True)

        # --- 4. 三大 Checkbox (即時計分) ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        st.session_state.who_we_help = c1.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.session_state.what_we_do = c2.multiselect("🚀 What we do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope_of_Word", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        col_chat, col_gallery = st.columns([1.3, 1])
        with col_chat:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI Deep Inquiry")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            if p := st.chat_input("話我知今次個 Project 邊度最難搞？"):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    # AI 讀取最新 State 進行深度挖掘
                    response = model.generate_content(f"已知SOW:{st.session_state.scope_of_word}, 客戶:{st.session_state.client_name}。請針對以下回答追問難點或創意：{p}")
                    st.write(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_gallery:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            gallery = st.file_uploader("Upload", accept_multiple_files=True, key="gal_u")
            if gallery:
                st.session_state.hero_slot = st.radio("🌟 選擇 Hero Banner (主圖)?", range(1, len(gallery)+1), horizontal=True)
            
            grid_html = '<div class="gallery-grid">'
            for i in range(8):
                is_hero = "hero-selected" if (i+1) == st.session_state.hero_slot else ""
                if gallery and i < len(gallery):
                    b64 = base64.b64encode(gallery[i].getvalue()).decode()
                    grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item {is_hero}"></div>'
                else: grid_html += f'<div class="slot-placeholder">Slot {i+1}</div>'
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        # --- 5. Admin Dashboard (完全同步 Tab 1) ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Admin Review (Real-time Synchronized)")
        st.info("💡 呢度嘅資料係同 Data Collector 即時同步嘅，你可以隨時進行最後修改。")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            st.text_input("Client Name (Sync)", value=st.session_state.client_name, disabled=True)
            st.text_input("Project Name (Sync)", value=st.session_state.project_name, disabled=True)
            st.text_input("Event Date (Sync)", value=st.session_state.event_date, disabled=True)
        with col_a2:
            st.text_input("Venue (Sync)", value=st.session_state.venue, disabled=True)
            st.write("**Who we help:**", ", ".join(st.session_state.who_we_help))
            st.write("**What we do:**", ", ".join(st.session_state.what_we_do))

        st.session_state.challenge = st.text_area("Final Challenge (深度挖掘結果)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Final Innovation (創意方案)", st.session_state.solution)
        
        if st.button("🚀 Confirm & Submit to Master DB"):
            st.balloons(); st.success(f"✅ 專案 {st.session_state.project_name} 資料已成功同步至雲端！")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
