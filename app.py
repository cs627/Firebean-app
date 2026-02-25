import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import time
import json
from PIL import Image, ImageEnhance, ImageOps
from rembg import remove  # <--- 核心：AI 去背景
from datetime import datetime

# --- 1. 定義環境 URL ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwLR9MVr4rNgCQeXd2zGq43_F3ncsml_t7IP4OkjqBNtdNiv0ETitiuzx4oif3T0tCZ/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbya_pl6h99zY_LrURojCL86c20NwxdeW6V9bhCXqgPjJdz2NVPgeFThthcR6gfw0d1P/exec"

# --- 2. 核心功能：Manna Logo 處理器 ---
def process_manna_logo(logo_file):
    """將上傳的 Logo 去背景並生成黑、白兩色高對比版本"""
    with st.spinner("🎨 Manna AI 正在進行 Logo 提煉 (去背景 & 黑白化)..."):
        input_image = Image.open(logo_file)
        
        # 1. AI 去背景 (使用 rembg)
        no_bg = remove(input_image)
        
        # 2. 生成「純白透明版」 (White Logo for Black Panel)
        white_logo = no_bg.convert("RGBA")
        data = white_logo.getdata()
        new_white = []
        for item in data:
            if item[3] > 0: # 如果像素不是透明的
                new_white.append((255, 255, 255, item[3]))
            else:
                new_white.append(item)
        white_logo.putdata(new_white)

        # 3. 生成「純黑透明版」 (Black Logo for White Web)
        black_logo = no_bg.convert("RGBA")
        data = black_logo.getdata()
        new_black = []
        for item in data:
            if item[3] > 0:
                new_black.append((0, 0, 0, item[3]))
            else:
                new_black.append(item)
        black_logo.putdata(new_black)

        # 輔助函數：轉為 Base64
        def to_b64(img):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()

        return to_b64(white_logo), to_b64(black_logo)

# --- 3. 初始化 Session State ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", 
        "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "messages": [], "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, 
        "logo_white": "", "logo_black": "" # 儲存處理後的 Logo
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# ... (保留 manna_ai_enhance 同 sync_data 函數) ...

# --- 4. Main App UI ---
def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 進度計算 (12維度：加入 Logo 狀態)
    filled = sum([1 for f in ["client_name", "project_name", "venue", "challenge", "solution"] if st.session_state[f]])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.project_photos else 0)
    filled += (1 if st.session_state.logo_white else 0) + (1 if st.session_state.ai_content else 0)
    percent = int((filled / 11) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=220)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Admin Review & Ecosystem Sync"])

    with tab1:
        # --- Logo 品牌處理區 ---
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Branding Assets (Client Logo)")
        lc1, lc2 = st.columns([1, 2])
        with lc1:
            logo_input = st.file_uploader("Upload Client Logo", type=['png', 'jpg', 'jpeg'], key="logo_up")
            if logo_input:
                if st.button("✨ Manna AI Refine Logo"):
                    w_b64, b_b64 = process_manna_logo(logo_input)
                    st.session_state.logo_white = w_b64
                    st.session_state.logo_black = b_b64
                    st.success("Logo 去背景及黑白對比版本已完成！")
        
        with lc2:
            if st.session_state.logo_white:
                sc1, sc2 = st.columns(2)
                sc1.image(f"data:image/png;base64,{st.session_state.logo_white}", caption="White (for Dark Slides)", width=120)
                sc2.image(f"data:image/png;base64,{st.session_state.logo_black}", caption="Black (for White Web)", width=120)
        st.markdown('</div>', unsafe_allow_html=True)

        # ... (保留原本的 Basic Info, Who We Help, AI Chatbot 同 Manna Gallery 區域) ...

    with tab2:
        # --- Admin Review & Sync ---
        # ... (保留文字生成區域) ...

        if st.button("🚀 Confirm & Sync to Firebean Ecosystem"):
            # 準備相片 Base64
            b64_images = []
            for i in range(len(st.session_state.project_photos)):
                img = st.session_state.processed_photos.get(i, Image.open(st.session_state.project_photos[i]))
                buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85)
                b64_images.append(base64.b64encode(buf.getvalue()).decode())

            # 構建 36 欄位 Payload
            payload = {
                "client_name": st.session_state.client_name,
                "project_name": st.session_state.project_name,
                "event_date": st.session_state.event_date,
                "venue": st.session_state.venue,
                "scope_of_work": ", ".join(st.session_state.scope_of_word),
                "category_who": ", ".join(st.session_state.who_we_help),
                "category_what": ", ".join(st.session_state.what_we_do),
                "challenge": st.session_state.challenge,
                "solution": st.session_state.solution,
                "ai": st.session_state.ai_content,
                "images": b64_images,
                "logo_white": st.session_state.logo_white, # <--- 同步黑白 Logo 到雲端
                "logo_black": st.session_state.logo_black
            }

            res_sheet = sync_data(SHEET_SCRIPT_URL, payload)
            if "Success" in res_sheet:
                st.balloons(); st.success("✅ 資料、相片及黑白雙色 Logo 已成功歸位！")
            else:
                st.error(f"同步出錯: {res_sheet}")

# ... (保留 apply_styles 同其他輔助函數) ...

if __name__ == "__main__": main()
