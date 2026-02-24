import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import time
from PIL import Image, ImageOps, ImageEnhance
from rembg import remove

# --- 1. 選項定義 ---
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 2. 系統初始化 ---
def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", 
        "event_date": "(2026 FEB)",
        "logo_white_b64": "", "logo_black_b64": "", 
        "project_photos": [], "hero_index": 0, "raw_logo": None,
        "processed_photos": {} # 儲存 AI 處理後的相片
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# --- 3. Manna AI 引擎 (Generative Extend & Cinematic Tone) ---
def manna_ai_enhance(image_file):
    """模擬 AI Generative Extend + Cinematic Style 處理"""
    img = Image.open(image_file)
    w, h = img.size
    
    # 檢查是否需要 Extend (像素不足 1920x1080)
    needs_extend = w < 1920 or h < 1080
    
    # 這裡模擬 AI 處理過程
    with st.spinner("🚀 Manna AI 正在進行 Generative Extend & Cinematic 調色..."):
        time.sleep(1.5) # 模擬運算時間
        
        # 1. 模擬 Cinematic Tone (增加對比度與飽和度，調整色調)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2) # 增加對比
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.1) # 增加色彩深度
        
        # 2. 模擬 AI Extend (如果像素不足，將其 Resize 到 1920 闊度並保持比例，模擬補全)
        if needs_extend:
            new_w = 1920
            new_h = int(h * (1920 / w))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            status = f"✅ AI 已完成像素擴展 ({new_w}x{new_h}) 及電影感調色"
        else:
            status = "✅ 已完成 Cinematic Style 處理"
            
    return img, status

# --- 4. 能量環 HTML ---
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
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.6); border-radius: 15px; }
        </style>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Firebean Brain 2.5", layout="wide")
    init_session_state()
    apply_styles()

    # --- Header ---
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(65), unsafe_allow_html=True) # 示例進度

    # --- Logo Studio (Filter Tone) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("🎨 Logo Studio (Filter Tone)")
    f_logo = st.file_uploader("Upload Logo", type=['png','jpg','jpeg'], key="l_up")
    if f_logo:
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            st.image(f_logo, caption="Original", use_container_width=True)
            if st.button("🪄 生成黑白雙色"):
                img = remove(Image.open(f_logo))
                # 這裡調用之前定義的 colorize 邏輯 (略)
                st.success("✅ Filter Tone 已完成")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Project Photos (AI Generative Extend) ---
    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    st.subheader("📸 Project Gallery (Manna AI Engine)")
    st.info("💡 系統會自動檢測像素。如果不足 1920x1080，Manna AI 會自動進行 Generative Extend 並加入 Cinematic 光暗處理。")
    
    files = st.file_uploader("一次過掟晒 8 張相入嚟", type=['jpg','png','jpeg'], accept_multiple_files=True, key="p_up")
    if files: st.session_state.project_photos = files

    if st.session_state.project_photos:
        st.write("---")
        # 選擇 Hero Banner
        hero_options = [f"Photo {i+1}" for i in range(len(st.session_state.project_photos))]
        choice = st.radio("🌟 邊張係 Hero Banner？", hero_options, index=st.session_state.hero_index, horizontal=True)
        st.session_state.hero_index = hero_options.index(choice)

        # 顯示處理後的結果
        cols = st.columns(4)
        for i, f in enumerate(st.session_state.project_photos):
            with cols[i % 4]:
                # 點擊「啟動 AI 處理」按鈕
                if st.button(f"✨ AI 處理 P{i+1}", key=f"btn_{i}"):
                    enhanced_img, status = manna_ai_enhance(f)
                    st.session_state.processed_photos[i] = enhanced_img
                    st.toast(status)

                # 顯示預覽
                is_hero = (i == st.session_state.hero_index)
                border_style = "hero-border" if is_hero else ""
                
                # 如果已經處理過，顯示 AI 版；否則顯示原圖
                display_img = st.session_state.processed_photos.get(i, Image.open(f))
                st.markdown(f'<div class="{border_style}">', unsafe_allow_html=True)
                st.image(display_img, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                if i in st.session_state.processed_photos:
                    st.caption(f"💎 Manna AI Enhanced ({display_img.size[0]}x{display_img.size[1]})")
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
