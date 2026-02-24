import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
from PIL import Image
from rembg import remove

# --- 1. 選項定義 ---
WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 2. 初始化 ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", 
        "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "logo_white_b64": "", "logo_black_b64": "", "messages": [], "gallery_slots": [None] * 8,
        "raw_logo": None
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！「+ ADD」已經成功「歸位」格仔中間喇！🥺"}]

# --- 3. 能量環進度條 (160px) ---
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
        
        /* 極簡 Slot 佈局 */
        .drag-text { font-size: 10px; color: #888; text-align: center; margin-bottom: 4px; pointer-events: none; position: relative; z-index: 5; }
        .slot-box { 
            position: relative; width: 100%; aspect-ratio: 1/1; 
            background: #E0E5EC; border-radius: 20px; 
            box-shadow: inset 6px 6px 12px #bec3c9, inset -6px -6px 12px #ffffff;
            overflow: visible; display: flex; align-items: center; justify-content: center;
        }
        .hero-mode { border: 4px solid #FF0000; box-shadow: 0 0 20px rgba(255,0,0,0.3); }
        
        /* 核心修復：強制 + ADD 居中於 Slot 內部 */
        .add-label { 
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%); /* 完美的幾何中心 */
            font-size: 36px; 
            font-weight: 900; 
            color: #FF4B4B; 
            pointer-events: none; 
            z-index: 5;
            text-align: center;
            width: 100%;
            opacity: 0.8;
        }
        
        /* 隱形上傳器全覆蓋 */
        .stFileUploader { position: absolute; top: 0; left: 0; width: 100% !important; height: 100% !important; z-index: 20 !important; opacity: 0; cursor: pointer; }
        .stFileUploader section { width: 100% !important; height: 100% !important; border: none !important; padding: 0 !important; }
        .stFileUploader label, .stFileUploader div { display: none !important; }
        
        img { pointer-events: none; border-radius: 16px; object-fit: cover; width: 100%; height: 100%; }
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

    # --- ⚖️ 計分系統 (11 點感應) ---
    score = 0
    if st.session_state.client_name: score += 1
    if st.session_state.project_name: score += 1
    if st.session_state.venue: score += 1
    if st.session_state.event_date: score += 1
    if st.session_state.who_we_help: score += 1
    if st.session_state.what_we_do: score += 1
    if st.session_state.scope_of_word: score += 1
    if st.session_state.logo_white_b64: score += 1
    if st.session_state.gallery_slots[0]: score += 1
    if st.session_state.challenge: score += 1
    if st.session_state.solution: score += 1
    final_percent = int((score / 11) * 100)

    # --- Header ---
    c_h1, c_h2 = st.columns([1, 1])
    with c_h1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c_h2: st.markdown(get_circle_progress_html(final_percent), unsafe_allow_html=True)

    # --- 2. Logo Studio (置頂，Slot 置中) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Studio")
    l1, l2, l3 = st.columns(3)
    with l1:
        st.markdown('<div class="drag-text">drag and drop</div>', unsafe_allow_html=True)
        st.markdown('<div class="slot-box">', unsafe_allow_html=True)
        if st.session_state.raw_logo: st.image(Image.open(st.session_state.raw_logo))
        else: st.markdown('<div class="add-label">+ ADD</div>', unsafe_allow_html=True)
        f_l = st.file_uploader("", type=['png','jpg','jpeg'], key="l_up")
        if f_l: st.session_state.raw_logo = f_l; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        if st.session_state.raw_logo and st.button("🪄 生成雙色"):
            img = remove(Image.open(st.session_state.raw_logo))
            st.session_state.logo_white_b64 = base64.b64encode(io.BytesIO(colorize_logo(img, (255,255,255)).tobytes()).getvalue()).decode()
            st.session_state.logo_black_b64 = base64.b64encode(io.BytesIO(colorize_logo(img, (0,0,0)).tobytes()).getvalue()).decode()
            st.rerun()
    with l2:
        if st.session_state.logo_white_b64:
            st.markdown('<div class="drag-text">white</div>', unsafe_allow_html=True)
            st.markdown('<div class="slot-box" style="background:#2D3436;"><img src="data:image/png;base64,'+st.session_state.logo_white_b64+'"></div>', unsafe_allow_html=True)
    with l3:
        if st.session_state.logo_black_b64:
            st.markdown('<div class="drag-text">black</div>', unsafe_allow_html=True)
            st.markdown('<div class="slot-box"><img src="data:image/png;base64,'+st.session_state.logo_black_b64+'"></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Collector", "📋 Review"])
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
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope_of_Word", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.3, 1])
        with cl:
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

        with cr:
            # Gallery Slot 佈置
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery")
            for r in range(2):
                cols = st.columns(4)
                for c in range(4):
                    idx = r * 4 + c
                    with cols[c]:
                        st.markdown('<div class="drag-text">drag and drop</div>', unsafe_allow_html=True)
                        h_mode = "hero-mode" if idx == 0 else ""
                        st.markdown(f'<div class="slot-box {h_mode}">', unsafe_allow_html=True)
                        if st.session_state.gallery_slots[idx]:
                            st.image(Image.open(st.session_state.gallery_slots[idx]))
                        else:
                            st.markdown('<div class="add-label">+ ADD</div>', unsafe_allow_html=True)
                        f = st.file_uploader("", type=['jpg','png','jpeg'], key=f"s_{idx}")
                        if f: st.session_state.gallery_slots[idx] = f; st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
