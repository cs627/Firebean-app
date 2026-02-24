import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import json
import re
from PIL import Image
from rembg import remove

# --- 1. 選項定義 (2026 最新 Website & PR 規格) ---
WHO_WE_HELP_OPTIONS = [
    "GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", 
    "F&B & HOSPITALITY", "MALLS & VENUES"
]

WHAT_WE_DO_OPTIONS = [
    "ROVING EXHIBITIONS", "SOCIAL & CONTENT", 
    "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"
]

# 最新修訂的 Scope_of_Word 清單 (加入 Souvenir Sourcing)
SOW_OPTIONS = [
    "Event Planning", "Event Coordination", "Event Production",
    "Theme Design", "Concept Development", "Social Media Management",
    "KOL / MI Line up", "Artist Endorsement", "Media Pitching", 
    "PR Consulting", "Souvenir Sourcing"
]

# --- 2. 系統初始化 ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_date": "", 
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "logo_white_b64": "", "logo_black_b64": "", "messages": []
    }
    for field, default in fields.items():
        if field not in st.session_state: st.session_state[field] = default
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！資料填好後，我哋深入傾吓今次個 Project 嘅難度同創意位？🥺"}]

# --- 3. 紅霓虹泥膠圓形進度條 (直徑 160px) ---
def get_circle_progress_html(percent):
    circumference = 439.8
    offset = circumference * (1 - percent/100)
    return f"""
    <div class="header-right-container">
        <div class="neu-circle-bg">
            <svg width="160" height="160">
                <defs>
                    <filter id="red-neon-glow">
                        <feGaussianBlur stdDeviation="3" result="cb"/>
                        <feMerge><feMergeNode in="cb"/><feMergeNode in="SourceGraphic"/></feMerge>
                    </filter>
                </defs>
                <circle stroke="#d1d9e6" stroke-width="12" fill="transparent" r="70" cx="80" cy="80"/>
                <circle stroke="#FF0000" stroke-width="12" stroke-dasharray="{circumference}" stroke-dashoffset="{offset}" 
                    stroke-linecap="round" fill="transparent" r="70" cx="80" cy="80" filter="url(#red-neon-glow)" 
                    style="transition: stroke-dashoffset 0.8s; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div class="progress-text">{percent}<span style="font-size:16px;">%</span></div>
        </div>
    </div>
    <style>
    .header-right-container {{ display: flex; justify-content: flex-end; align-items: center; }}
    .neu-circle-bg {{ position: relative; width: 160px; height: 160px; border-radius: 50%; background: #E0E5EC; 
        box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center; }}
    .progress-text {{ position: absolute; font-size: 38px; font-weight: 900; color: #2D3436; font-family: 'Arial Black'; text-shadow: 1px 1px 2px #ffffff; }}
    </style>
    """

def apply_styles():
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
    
    # 進度計算 (9項基準)
    track_fields = ["client_name", "project_name", "venue", "event_date", "challenge", "solution"]
    filled_count = sum(1 for f in track_fields if st.session_state[f])
    has_who = 1 if st.session_state.who_we_help else 0
    has_what = 1 if st.session_state.what_we_do else 0
    has_sow = 1 if st.session_state.scope_of_word else 0
    percent = int(((filled_count + has_who + has_what + has_sow) / 9) * 100)
    
    with col_h2:
        st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    # --- 2. Logo Studio (置頂，不隱藏) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Studio (黑白雙色去背生成)")
    l_col1, l_col2 = st.columns([1, 2])
    with l_col1:
        logo_f = st.file_uploader("上傳客戶標誌", type=['png','jpg','jpeg'], key="logo_up")
        if st.button("🪄 一鍵生成雙色版") and logo_f:
            img_nobg = remove(Image.open(logo_f))
            w_img = colorize_logo(img_nobg, (255,255,255)); b_img = colorize_logo(img_nobg, (0,0,0))
            buf_w, buf_b = io.BytesIO(), io.BytesIO()
            w_img.save(buf_w, format="PNG"); b_img.save(buf_b, format="PNG")
            st.session_state.logo_white_b64 = base64.b64encode(buf_w.getvalue()).decode()
            st.session_state.logo_black_b64 = base64.b64encode(buf_b.getvalue()).decode()
            st.rerun()
    with l_col2:
        if st.session_state.logo_white_b64:
            c1, c2 = st.columns(2)
            c1.image(f"data:image/png;base64,{st.session_state.logo_white_b64}", caption="White (Dark BG)")
            c2.image(f"data:image/png;base64,{st.session_state.logo_black_b64}", caption="Black (Light BG)")
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Dashboard"])

    with tab1:
        # --- 3. Fill in the Blanks ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Basic Information")
        b1, b2, b3, b4 = st.columns(4)
        st.session_state.client_name = b1.text_input("客戶名稱", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("項目名稱", st.session_state.project_name)
        st.session_state.event_date = b3.text_input("日期時間", st.session_state.event_date)
        st.session_state.venue = b4.text_input("活動地點", st.session_state.venue)
        st.markdown('</div>', unsafe_allow_html=True)

        # --- 4. 三位一體 Checkbox (包含 Souvenir Sourcing) ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("👥 Who we help")
            sel_who = st.multiselect("網站分類", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        with c2:
            st.subheader("🚀 What we do")
            sel_what = st.multiselect("網站服務", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        with c3:
            st.subheader("🛠️ Scope_of_Word")
            sel_sow = st.multiselect("PR 具體執行項目", SOW_OPTIONS, default=st.session_state.scope_of_word)
        
        if st.button("確認所有勾選"):
            st.session_state.who_we_help, st.session_state.what_we_do, st.session_state.scope_of_word = sel_who, sel_what, sel_sow
            st.session_state.messages.append({"role": "user", "content": "已更新類別與執行項目。"})
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        col_chat, col_gallery = st.columns([1.3, 1])
        with col_chat:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI Deep Inquiry")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])

            if p := st.chat_input("分享今次 Project 最難搞嘅位..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    prompt = f"PR背景:Who={st.session_state.who_we_help}, What={st.session_state.what_we_do}, SOW={st.session_state.scope_of_word}。\n針對User嘅回答進行深度追問，重點在於難點、創意、遊戲玩法及執行細節：{p}"
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                    st.write(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_gallery:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Project Gallery (8 Slots)")
            gallery = st.file_uploader("Upload", accept_multiple_files=True, key="gal_u")
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
        st.session_state.challenge = st.text_area("The Hardest Part (Challenge)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Our Innovation (Solution)", st.session_state.solution)
        WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyAjp74aiUDfsAyqwK_nDDu0q128ZL9az9yrC9201H6vYJ_gY8qI17962cLSWMexfiL/exec"
        if st.button("🚀 Confirm & Submit to Master DB"):
            payload = {
                "client": st.session_state.client_name, "project": st.session_state.project_name,
                "who_we_help": ", ".join(st.session_state.who_we_help), "what_we_do": ", ".join(st.session_state.what_we_do),
                "scope_of_word": ", ".join(st.session_state.scope_of_word), "challenge": st.session_state.challenge, "solution": st.session_state.solution
            }
            requests.post(WEBHOOK_URL, json=payload)
            st.balloons(); st.success("✅ 資料同步成功！")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
