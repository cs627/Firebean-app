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
CATEGORY_OPTIONS = ["Government", "Corporate", "Luxury", "F&B", "Tech", "Other"]

# --- 2. 系統初始化 ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "challenge": "", "solution": "", 
        "category": "Corporate", "scope_of_word": [], "logo_white_b64": "", "logo_black_b64": "", "debug_logs": []
    }
    for field, default in fields.items():
        if field not in st.session_state: st.session_state[field] = default
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！Red Neon 模式已啟動。請先勾選 Scope_of_Word，我再幫你執報告！🥺"}]

# --- 3. 紅霓虹泥膠圓形進度條 (直徑對標 Logo) ---
def get_circle_progress_html(percent):
    circumference = 439.8
    offset = circumference * (1 - percent/100)
    return f"""
    <div class="header-right-container">
        <div class="neu-circle-bg">
            <svg class="progress-ring" width="160" height="160">
                <defs>
                    <filter id="red-neon-glow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                <circle class="progress-ring__circle_bg" stroke="#d1d9e6" stroke-width="12" fill="transparent" r="70" cx="80" cy="80"/>
                <circle class="progress-ring__circle" stroke="#FF0000" stroke-width="12" stroke-dasharray="{circumference}" 
                    stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="70" cx="80" cy="80"
                    filter="url(#red-neon-glow)" />
            </svg>
            <div class="progress-text">{percent}<span style="font-size:16px;">%</span></div>
        </div>
    </div>
    <style>
    .header-right-container {{ display: flex; justify-content: flex-end; align-items: center; height: 160px; }}
    .neu-circle-bg {{
        position: relative; width: 160px; height: 160px; border-radius: 50%;
        background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff;
        display: flex; align-items: center; justify-content: center;
    }}
    .progress-ring__circle {{ transition: stroke-dashoffset 0.8s ease-in-out; transform: rotate(-90deg); transform-origin: 50% 50%; filter: drop-shadow(0 0 10px #FF0000); }}
    .progress-text {{ position: absolute; font-size: 38px; font-weight: 900; color: #2D3436; font-family: 'Arial Black'; text-shadow: 1px 1px 2px #ffffff; }}
    </style>
    """

def apply_neu_theme():
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

def log_event(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append(f"[{timestamp}] {level}: {msg}")

def main():
    st.set_page_config(page_title="Firebean Brain Neon", layout="wide")
    init_session_state()

    # --- 1. Header (Logo & Progress 平排) ---
    col_logo, col_progress = st.columns([1, 1])
    with col_logo:
        st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    
    current_percent = apply_neu_theme()
    with col_progress:
        st.markdown(get_circle_progress_html(current_percent), unsafe_allow_html=True)

    # --- 2. Logo Studio (絕對置頂於 Logo 下方) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Studio (黑白雙色去背生成)")
    l_col1, l_col2 = st.columns([1, 2])
    with l_col1:
        logo_f = st.file_uploader("上傳原始 Logo", type=['png','jpg','jpeg'], key="logo_top")
        if st.button("🪄 一鍵生成雙色版") and logo_f:
            with st.spinner("霓虹處理中..."):
                img_nobg = remove(Image.open(logo_f))
                white_img = colorize_logo(img_nobg, (255,255,255))
                black_img = colorize_logo(img_nobg, (0,0,0))
                buf_w, buf_b = io.BytesIO(), io.BytesIO()
                white_img.save(buf_w, format="PNG"); black_img.save(buf_b, format="PNG")
                st.session_state.logo_white_b64 = base64.b64encode(buf_w.getvalue()).decode()
                st.session_state.logo_black_b64 = base64.b64encode(buf_b.getvalue()).decode()
                st.rerun()

    with l_col2:
        if st.session_state.logo_white_b64:
            pre1, pre2 = st.columns(2)
            pre1.image(f"data:image/png;base64,{st.session_state.logo_white_b64}", caption="白色版 (深底用)", use_column_width=True)
            pre2.image(f"data:image/png;base64,{st.session_state.logo_black_b64}", caption="黑色版 (淺底用)", use_column_width=True)
        else:
            st.info("💡 上傳標誌後會在此生成黑色與白色去背版本。")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. 影像管理 Expander ---
    with st.expander("🖼️ 影像資產管理 (自動檢測像素)", expanded=False):
        gallery = st.file_uploader("拖放 8 張相片", accept_multiple_files=True, type=['jpg','png','jpeg'])

    # --- 4. 主要工作區 ---
    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Dashboard"])

    with tab1:
        col_chat, col_gallery = st.columns([1.3, 1])
        with col_chat:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if not st.session_state.scope_of_word:
                st.info("請勾選今次涉及的工作範疇：")
                selected = st.multiselect("Scope_of_Word", SOW_OPTIONS, key="chat_sow")
                if st.button("確認勾選"):
                    st.session_state.scope_of_word = selected
                    st.session_state.messages.append({"role": "user", "content": f"已揀：{', '.join(selected)}"})
                    st.rerun()

            if p := st.chat_input("輸入挑戰與解決方案..."):
                # 優先試 Gemini 3 Flash
                models_to_try = ["gemini-3-flash", "gemini-2.5-flash"]
                response = None
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                
                with st.chat_message("assistant"):
                    for m_name in models_to_try:
                        try:
                            log_event(f"嘗試模型: {m_name}")
                            model = genai.GenerativeModel(m_name)
                            response = model.generate_content(f"SOW Context: {st.session_state.scope_of_word}\nUser: {p}")
                            log_event(f"成功使用: {m_name}", "SUCCESS")
                            break
                        except Exception as e:
                            log_event(f"模型 {m_name} 失敗: {str(e)}", "WARNING")
                    
                    if response:
                        st.write(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_gallery:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery (8 Slots)")
            grid_html = '<div class="gallery-grid">'
            for i in range(8):
                if gallery and i < len(gallery):
                    b64 = base64.b64encode(gallery[i].getvalue()).decode()
                    grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item"></div>'
                else:
                    grid_html += f'<div class="slot-placeholder">Slot {i+1}</div>'
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 Admin Review")
        st.session_state.category = st.selectbox("Category", CATEGORY_OPTIONS, index=CATEGORY_OPTIONS.index(st.session_state.category))
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.scope_of_word = st.multiselect("Scope_of_Word", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.session_state.challenge = st.text_area("Challenge", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution", st.session_state.solution)
        
        WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyAjp74aiUDfsAyqwK_nDDu0q128ZL9az9yrC9201H6vYJ_gY8qI17962cLSWMexfiL/exec"
        if st.button("🚀 Confirm & Submit to Master DB"):
            try:
                payload = {
                    "category": st.session_state.category,
                    "project": st.session_state.project_name,
                    "scope_of_word": ", ".join(st.session_state.scope_of_word),
                    "logo_white": st.session_state.logo_white_b64,
                    "logo_black": st.session_state.logo_black_b64
                }
                requests.post(WEBHOOK_URL, json=payload)
                st.balloons(); st.success("✅ 資料已同步！")
            except Exception as e: st.error(f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 5. Debug Zone ---
    st.markdown("---")
    with st.expander("🛠️ 系統運行日誌 (Debug Zone)"):
        for log in st.session_state.debug_logs[-15:]:
            st.write(log)

if __name__ == "__main__": main()
