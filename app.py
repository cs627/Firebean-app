import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
from PIL import Image
from rembg import remove

# --- 1. 選項定義 (同步最新清單) ---
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
        "project_photos": [], # 改為儲存多個檔案的列表
        "hero_index": 0, # 預設第一張為 Hero
        "raw_logo": None
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！已回歸經典大盒設計。請將所有相片一次過掟入去，然後喺下面揀 Hero！🥺"}]

# --- 3. 進度條 HTML (160px) ---
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
        
        /* 大上傳盒樣式 */
        .large-upload-box {
            border: 3px dashed #bec3c9;
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            background: #E0E5EC;
            color: #888;
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 20px;
        }
        .large-upload-box:hover { border-color: #FF4B4B; color: #FF4B4B; }
        
        /* 縮圖預覽區 */
        .thumbnail-container {
            display: flex; flex-direction: column; align-items: center; margin-bottom: 10px;
        }
        .thumbnail-img { 
            width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 12px; 
            box-shadow: 3px 3px 6px #bec3c9, -3px -3px 6px #ffffff;
        }
        .hero-thumbnail { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.5); }

        /* 隱藏 Streamlit 原生上傳樣式，用 CSS 覆蓋 */
        .stFileUploader > div > div { width: 100%; }
        .stFileUploader > div > div > button { display: none; }
        .stFileUploader label {
            display: block; width: 100%; height: 100%; 
            border: 3px dashed #bec3c9; border-radius: 20px; padding: 40px 0;
            text-align: center; font-weight: bold; color: #888; cursor: pointer;
        }
        .stFileUploader label:hover { border-color: #FF4B4B; color: #FF4B4B; }
        .stFileUploader label::before { content: '📤 Drag photos here / Open file'; font-size: 16px; }
        
        /* Logo 上傳區特定樣式 */
        .logo-uploader > div > div > label::before { content: '🎨 Drag logo here / Open file'; }

        /* Radio Button 樣式調整 */
        .stRadio > div { flex-direction: row; align-items: center; justify-content: center; }
        </style>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain 2.5", layout="wide")
    init_session_state()
    apply_styles()

    # --- ⚖️ 全方位計分系統 ---
    score = 0
    if st.session_state.client_name: score += 1
    if st.session_state.project_name: score += 1
    if st.session_state.venue: score += 1
    if st.session_state.event_date: score += 1
    if st.session_state.who_we_help: score += 1
    if st.session_state.what_we_do: score += 1
    if st.session_state.scope_of_word: score += 1
    if st.session_state.logo_white_b64: score += 1
    if st.session_state.project_photos: score += 1 # 有上傳相片就計分
    if st.session_state.challenge: score += 1
    if st.session_state.solution: score += 1
    final_percent = int((score / 11) * 100)

    # --- 1. Header ---
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(final_percent), unsafe_allow_html=True)

    # --- 2. Logo Assets (大盒 + 預覽) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Assets")
    
    # Logo 上傳大盒
    st.markdown('<div class="logo-uploader">', unsafe_allow_html=True)
    f_logo = st.file_uploader("", type=['png','jpg','jpeg'], key="logo_uploader")
    st.markdown('</div>', unsafe_allow_html=True)
    if f_logo: st.session_state.raw_logo = f_logo

    if st.session_state.raw_logo:
        # Logo 處理按鈕
        if st.button("🪄 Process Logo (Generate White & Black)"):
            from rembg import remove
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
            
        # Logo 預覽區 (原圖、白、黑)
        st.write("---")
        l_c1, l_c2, l_c3 = st.columns(3)
        with l_c1:
            st.caption("Original")
            st.image(Image.open(st.session_state.raw_logo), use_column_width=True)
        with l_c2:
            if st.session_state.logo_white_b64:
                st.caption("White (Dark BG)")
                st.markdown(f'<div style="background:#2D3436;border-radius:12px;padding:10px;"><img src="data:image/png;base64,{st.session_state.logo_white_b64}" style="width:100%;"></div>', unsafe_allow_html=True)
        with l_c3:
            if st.session_state.logo_black_b64:
                st.caption("Black (Light BG)")
                st.markdown(f'<div style="background:#E0E5EC;border-radius:12px;padding:10px;"><img src="data:image/png;base64,{st.session_state.logo_black_b64}" style="width:100%;"></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Review"])
    with tab1:
        # Basic Info
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

        # Checkboxes
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        st.session_state.who_we_help = c1.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.session_state.what_we_do = c2.multiselect("🚀 What we do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        # AI Chatbot
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🤖 AI Assistant")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.write(msg["content"])
        if p := st.chat_input("Talk to AI..."):
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            st.session_state.messages.append({"role": "user", "content": p})
            with st.chat_message("user"): st.write(p)
            with st.chat_message("assistant"):
                model = genai.GenerativeModel("gemini-2.5-flash")
                res = model.generate_content(f"SOW Context: {st.session_state.scope_of_word}\nUser: {p}")
                st.write(res.text); st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.markdown('</div>', unsafe_allow_html=True)

        # --- 4. Project Photos (大盒 + 縮圖 + Hero 選擇) ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📸 Project Photos")
        
        # 多檔案上傳大盒
        files = st.file_uploader("", type=['jpg','png','jpeg'], accept_multiple_files=True, key="project_uploader")
        if files: st.session_state.project_photos = files

        # 縮圖預覽與 Hero 選擇
        if st.session_state.project_photos:
            st.write("---")
            st.write("🌟 **Select Hero Banner:**")
            
            # 使用 columns 排列縮圖
            cols = st.columns(4)
            for i, file in enumerate(st.session_state.project_photos):
                col_idx = i % 4
                with cols[col_idx]:
                    # Hero 樣式
                    hero_class = "hero-thumbnail" if i == st.session_state.hero_index else ""
                    st.markdown(f'<img src="data:image/png;base64,{base64.b64encode(file.getvalue()).decode()}" class="thumbnail-img {hero_class}">', unsafe_allow_html=True)
                    # Hero 選擇 Radio Button
                    if st.radio(f"Hero {i+1}", [i], key=f"hero_radio_{i}", index=0 if i == st.session_state.hero_index else -1, label_visibility="collapsed"):
                        st.session_state.hero_index = i
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
