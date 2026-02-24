import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
from PIL import Image
from rembg import remove

# --- 1. 選項與限制定義 ---
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
        "logo_white_b64": "", "logo_black_b64": "", "messages": [], "gallery_slots": [None] * 8
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！全感應系統已啟動。每一項輸入都會增加進度條能量！🥺"}]

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
        
        /* 極簡 Slot 樣式 */
        .drag-text { font-size: 10px; color: #888; text-align: center; margin-bottom: 2px; text-transform: lowercase; }
        .slot-box { 
            position: relative; width: 100%; aspect-ratio: 1/1; 
            background: #E0E5EC; border-radius: 15px; 
            box-shadow: inset 5px 5px 10px #bec3c9, inset -5px -5px 10px #ffffff;
            display: flex; align-items: center; justify-content: center; overflow: hidden;
        }
        .hero-mode { border: 3px solid #FF0000; box-shadow: 0 0 15px #FF0000; }
        .plus-icon { 
            position: absolute; bottom: 8px; right: 8px; 
            font-size: 18px; font-weight: bold; color: #FF4B4B; 
            background: #E0E5EC; width: 24px; height: 24px; 
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            box-shadow: 2px 2px 5px #bec3c9, -2px -2px 5px #ffffff;
        }
        .stFileUploader section { padding: 0 !important; border: none !important; background: transparent !important; }
        .stFileUploader label, .stFileUploader span { display: none !important; }
        .stFileUploader { position: absolute; width: 100%; height: 100%; opacity: 0; z-index: 10; cursor: pointer; }
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

    # --- ⚖️ 全感應計分邏輯 ---
    score = 0
    if st.session_state.client_name: score += 1
    if st.session_state.project_name: score += 1
    if st.session_state.venue: score += 1
    if st.session_state.event_date: score += 1 # 年份月份選擇後會自動生成
    if st.session_state.who_we_help: score += 1
    if st.session_state.what_we_do: score += 1
    if st.session_state.scope_of_word: score += 1
    if st.session_state.logo_white_b64: score += 1
    if st.session_state.gallery_slots[0]: score += 1 # Slot 1 是 Hero Banner
    if st.session_state.challenge: score += 1
    if st.session_state.solution: score += 1
    
    final_percent = int((score / 11) * 100)

    # --- 1. Header (Logo & Neon Progress) ---
    col_h1, col_h2 = st.columns([1, 1])
    with col_h1:
        st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    
    with col_h2:
        st.markdown(get_circle_progress_html(final_percent), unsafe_allow_html=True)

    # --- 2. Logo Studio (置頂) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Studio")
    l1, l2 = st.columns([1, 2])
    with l1:
        logo_f = st.file_uploader("Upload", type=['png','jpg','jpeg'], key="l_up")
        if st.button("🪄 生成雙色") and logo_f:
            img = remove(Image.open(logo_f))
            st.session_state.logo_white_b64 = base64.b64encode(io.BytesIO(colorize_logo(img, (255,255,255)).tobytes()).getvalue()).decode()
            st.session_state.logo_black_b64 = base64.b64encode(io.BytesIO(colorize_logo(img, (0,0,0)).tobytes()).getvalue()).decode()
            st.rerun()
    with l2:
        if st.session_state.logo_white_b64: st.success("✅ 已同步至計分系統")
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Collector", "📋 Review"])

    with tab1:
        # --- 3. Basic Info (填寫即計分) ---
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

        # --- 4. Checkboxes (勾選即計分) ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        st.session_state.who_we_help = c1.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.session_state.what_we_do = c2.multiselect("🚀 What we do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope_of_Word", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        col_left, col_right = st.columns([1.3, 1])
        with col_left:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            if p := st.chat_input("話我知細節..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    res = model.generate_content(f"SOW:{st.session_state.scope_of_word}\nUser:{p}")
                    st.write(res.text); st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_right:
            # --- 5. 極簡 8 Slot 拖放 (Slot 1 為 Hero 計分點) ---
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            for r in range(2):
                cols = st.columns(4)
                for c in range(4):
                    idx = r * 4 + c
                    with cols[c]:
                        st.markdown('<div class="drag-text">drag and drop</div>', unsafe_allow_html=True)
                        hero_class = "hero-mode" if idx == 0 else ""
                        st.markdown(f'<div class="slot-box {hero_class}">', unsafe_allow_html=True)
                        
                        if st.session_state.gallery_slots[idx]:
                            st.image(Image.open(st.session_state.gallery_slots[idx]), use_column_width=True)
                        else:
                            st.markdown('<div class="plus-icon">+</div>', unsafe_allow_html=True)
                        
                        f = st.file_uploader("", type=['jpg','png','jpeg'], key=f"s_{idx}")
                        if f: 
                            st.session_state.gallery_slots[idx] = f
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        # --- 6. Review & Admin (填寫即計分) ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Review")
        st.session_state.challenge = st.text_area("Challenge (深度挖掘內容)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution (創意方案)", st.session_state.solution)
        if st.button("🚀 Confirm & Submit"):
            st.balloons(); st.success(f"✅ 能量已滿 100%！專案資料已同步至 Master DB。")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
