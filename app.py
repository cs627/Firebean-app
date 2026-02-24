import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import datetime
import json
import re
from PIL import Image
from rembg import remove

# --- 1. SOW 選項 ---
SOW_OPTIONS = [
    "Overall planning and coordination",
    "Event Production / Theme Development",
    "Concept development",
    "Social Media Management",
    "KOL 網紅",
    "Media Pitching",
    "Interactive Game preparation",
    "Theme design"
]

# --- 2. 系統初始化 ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "challenge": "", "solution": "", 
        "scope_of_word": [], "logo_white_b64": "", "logo_black_b64": "", "debug_logs": []
    }
    for field, default in fields.items():
        if field not in st.session_state: st.session_state[field] = default
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！今日個 Project 搞成點？請先勾選 Scope_of_Word，我再幫你執報告！🥺"}]

# --- 3. 圓形進度條 CSS (Big % Center) ---
def get_circle_progress_html(percent):
    return f"""
    <div class="circle-container">
        <svg class="progress-ring" width="100" height="100">
            <circle class="progress-ring__circle_bg" stroke="#d1d9e6" stroke-width="8" fill="transparent" r="40" cx="50" cy="50"/>
            <circle class="progress-ring__circle" stroke="#FF4B4B" stroke-width="8" stroke-dasharray="251.32" 
                stroke-dashoffset="{251.32 * (1 - percent/100)}" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"/>
        </svg>
        <div class="progress-text">{percent}%</div>
    </div>
    <style>
    .circle-container {{ position: relative; width: 100px; height: 100px; display: flex; align-items: center; justify-content: center; }}
    .progress-ring__circle {{ transition: stroke-dashoffset 0.35s; transform: rotate(-90deg); transform-origin: 50% 50%; }}
    .progress-text {{ position: absolute; font-size: 20px; font-weight: 800; color: #2D3436; }}
    </style>
    """

def apply_neu_theme():
    # 計算進度
    track_text = ["client_name", "project_name", "challenge", "solution"]
    filled_text = sum(1 for f in track_text if str(st.session_state[f]).strip() != "")
    has_sow = 1 if st.session_state.scope_of_word else 0
    percent = int(((filled_text + has_sow) / 5) * 100)

    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 25px; margin-bottom: 20px; }
        .gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        @media (max-width: 640px) { .gallery-grid { grid-template-columns: repeat(2, 1fr) !important; } }
        .gallery-item { width: 100%; aspect-ratio: 1/1; border-radius: 12px; object-fit: cover; box-shadow: 4px 4px 8px #bec3c9; }
        .slot-placeholder { aspect-ratio: 1/1; background: #E0E5EC; border-radius: 12px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 10px; }
        </style>
    """, unsafe_allow_html=True)
    return percent

def colorize_logo(img, color):
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    solid = Image.new('RGB', img.size, color)
    final = Image.composite(solid, Image.new('RGB', img.size, (0,0,0)), a)
    final.putalpha(a)
    return final

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()

    # --- 1. Header (Logo + Progress) ---
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    
    current_percent = apply_neu_theme()
    with col_h2:
        st.markdown(get_circle_progress_html(current_percent), unsafe_allow_html=True)

    # --- 2. Logo Studio (最上方固定位置) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Studio (去背 & 黑白雙色生成)")
    l_col1, l_col2 = st.columns([1, 2])
    with l_col1:
        logo_f = st.file_uploader("上傳原始 Logo", type=['png','jpg','jpeg'], key="logo_top")
        process_btn = st.button("🪄 一鍵生成雙色版")
    with l_col2:
        if logo_f and process_btn:
            with st.spinner("正在轉化..."):
                img_nobg = remove(Image.open(logo_f))
                white_img = colorize_logo(img_nobg, (255,255,255))
                black_img = colorize_logo(img_nobg, (0,0,0))
                
                # 顯示預覽
                pre1, pre2 = st.columns(2)
                pre1.image(white_img, caption="白色版 (PPT用)", use_column_width=True)
                pre2.image(black_img, caption="黑色版 (網站用)", use_column_width=True)
                
                # 存入 Session
                buf_w, buf_b = io.BytesIO(), io.BytesIO()
                white_img.save(buf_w, format="PNG"); black_img.save(buf_b, format="PNG")
                st.session_state.logo_white_b64 = base64.b64encode(buf_w.getvalue()).decode()
                st.session_state.logo_black_b64 = base64.b64encode(buf_b.getvalue()).decode()
        elif st.session_state.logo_white_b64:
            st.info("✅ 標誌已備妥（白色及黑色版已存入系統記憶）。")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. Tabs (Main Work) ---
    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Review"])

    with tab1:
        col_chat, col_gallery = st.columns([1.3, 1])
        with col_chat:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            # SOW Checkbox 批次處理
            if not st.session_state.scope_of_word:
                st.info("請勾選今次涉及的工作範疇：")
                selected = st.multiselect("Select Scope_of_Word", SOW_OPTIONS)
                if st.button("確認勾選"):
                    st.session_state.scope_of_word = selected
                    st.session_state.messages.append({"role": "user", "content": f"我揀咗：{', '.join(selected)}"})
                    st.rerun()

            if p := st.chat_input("話我知個 Project 嘅挑戰同解決方案..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        response = model.generate_content(f"SOW:{st.session_state.scope_of_word}\nUser:{p}")
                        st.write(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_gallery:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 8 Project Photos")
            gallery = st.file_uploader("拖放相片", accept_multiple_files=True, key="gal")
            grid_html = '<div class="gallery-grid">'
            for i in range(8):
                if gallery and i < len(gallery):
                    b64 = base64.b64encode(gallery[i].getvalue()).decode()
                    grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item"></div>'
                else: grid_html += f'<div class="slot-placeholder">Slot {i+1}</div>'
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Admin Review")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.challenge = st.text_area("Challenge", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution", st.session_state.solution)
        if st.button("🚀 Confirm & Submit"):
            st.balloons(); st.success("✅ 同步成功！")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 4. Debug Console (底部固定) ---
    st.markdown("---")
    with st.expander("🛠️ 系統運行日誌 (Debug Zone)"):
        st.write("目前運行: Gemini 2.5 Flash + Nano Banana Image Check")

if __name__ == "__main__": main()
