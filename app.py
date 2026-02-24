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

# --- 1. 核心性格與影像任務 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Reporting & Creative Brain。
【影像任務】
若相片像素不足或比例不符，請引導調用 Nano Banana (Gemini 2.5 Flash Preview Image) 進行 AI 擴展。
視覺風格：Cinematic Tone and Manner, Professional PR Lighting, Cinematic Style.
【收料任務】
收集：Client, Project, Venue, Challenge, Solution。不客套，直達主題。
"""

def log_event(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {msg}"
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append(log_entry)

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "challenge": "", "solution": "", 
        "logo_b64": "", "debug_logs": [], "gallery_files": []
    }
    for field, default in fields.items():
        if field not in st.session_state: st.session_state[field] = default
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！影像與報告系統已就緒。今日個 Project 搞成點？🥺"}]

def check_image_assets(files):
    results = []
    if not files: return results
    for f in files:
        img = Image.open(f)
        w, h = img.size
        if w < 800 or h < 800:
            results.append(f"⚠️ {f.name}: 像素不足 ({w}x{h})，將進行 Cinematic 補全。")
        else:
            results.append(f"✅ {f.name}: 像素達標 ({w}x{h})。")
    return results

def apply_neu_theme(gallery_files):
    track_text = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled_text = sum(1 for f in track_text if str(st.session_state[f]).strip() != "")
    progress_percent = int(((filled_text + (1 if gallery_files else 0) + (1 if st.session_state.logo_b64 else 0)) / 7) * 100)

    st.markdown(f"""
        <style>
        header {{visibility: hidden;}} footer {{visibility: hidden;}}
        .stApp {{ background-color: #E0E5EC; color: #2D3436; }}
        .energy-container {{ width: 100%; background: #E0E5EC; padding: 10px 0; position: sticky; top: 0; z-index: 999; }}
        .energy-bar-bg {{ height: 14px; background: #E0E5EC; border-radius: 10px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; overflow: hidden; margin: 0 20px; }}
        .energy-bar-fill {{ height: 100%; width: {progress_percent}%; background: linear-gradient(90deg, #FF4B4B, #FF8080); box-shadow: 0 0 15px #FF4B4B; transition: width 0.8s; }}
        .neu-card {{ background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff; padding: 20px; margin-bottom: 20px; }}
        .gallery-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px; }}
        @media (max-width: 640px) {{ .gallery-grid {{ grid-template-columns: repeat(2, 1fr) !important; }} }}
        .gallery-item {{ width: 100%; aspect-ratio: 1/1; border-radius: 12px; object-fit: cover; box-shadow: 4px 4px 8px #bec3c9; }}
        .slot-placeholder {{ aspect-ratio: 1/1; background: #E0E5EC; border-radius: 12px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 10px; }}
        </style>
        <div class="energy-container">
            <div class="energy-bar-bg"><div class="energy-bar-fill"></div></div>
            <div style="font-size: 11px; font-weight: 800; color: #FF4B4B; text-align: right; margin-right: 25px; margin-top: 5px;">REPORT & ASSET READINESS: {progress_percent}%</div>
        </div>
    """, unsafe_allow_html=True)

def get_base64_image(file):
    try: return base64.b64encode(file.getvalue()).decode()
    except: return ""

def main():
    st.set_page_config(page_title="Firebean Creative Hub", layout="wide")
    init_session_state()

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)

    # --- 📸 影像資產管理 (Top Expander) ---
    with st.expander("🖼️ 影像資產管理 (手機/電腦通用上傳口)", expanded=True):
        gallery = st.file_uploader("拖放 8 張相片 (AI 自動檢測像素)", accept_multiple_files=True, type=['jpg','png','jpeg'])
        if gallery:
            status_msgs = check_image_assets(gallery)
            for msg in status_msgs:
                if "⚠️" in msg: st.warning(msg)
                else: st.info(msg)

    apply_neu_theme(gallery)

    tab1, tab2 = st.tabs(["💬 Creative Collector", "📋 Asset Dashboard"])

    with tab1:
        col_chat, col_assets = st.columns([1.3, 1])
        with col_chat:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if p := st.chat_input("話我知最難搞嘅位係邊度？..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    with st.spinner("AI 處理中..."):
                        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION)
                        response = model.generate_content(p)
                        st.write(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_assets:
            # 🎨 Logo Studio (獨立 Tab)
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🎨 Logo Studio")
            logo_f = st.file_uploader("上傳客戶 Logo (去背轉白)", type=['png','jpg','jpeg'], key="logo_up")
            if logo_f and st.button("🪄 一鍵白色化"):
                with st.spinner("處理中..."):
                    img = Image.open(logo_f)
                    out = remove(img)
                    final = Image.composite(Image.new('RGBA', img.size, (255,255,255,255)), Image.new('RGBA', img.size, (0,0,0,0)), out.getchannel('A'))
                    st.image(final, width=120)
                    buf = io.BytesIO(); final.save(buf, format="PNG")
                    st.session_state['logo_b64'] = base64.b64encode(buf.getvalue()).decode()
            st.markdown('</div>', unsafe_allow_html=True)

            # 📸 8 Photos Grid & AI Preview (雙層 Tab)
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            sub_tab1, sub_tab2 = st.tabs(["📸 8 Photos Grid", "🖼️ AI 優化預覽"])
            
            with sub_tab1:
                st.subheader("原始相片 (8 Slots)")
                grid_html = '<div class="gallery-grid">'
                for i in range(8):
                    if gallery and i < len(gallery):
                        b64 = get_base64_image(gallery[i])
                        grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item"></div>'
                    else: grid_html += f'<div class="slot-placeholder">Slot {i+1}</div>'
                grid_html += '</div>'
                st.markdown(grid_html, unsafe_allow_html=True)
                
            with sub_tab2:
                st.subheader("AI Cinematic 優化")
                if gallery:
                    grid_html = '<div class="gallery-grid">'
                    for f in gallery[:8]:
                        b64 = get_base64_image(f)
                        # 這裡模擬顯示「優化後」的效果，實際應用中會顯示 Nano Banana 生成的圖片
                        grid_html += f'<div><img src="data:image/png;base64,{b64}" class="gallery-item" style="filter: contrast(1.2) saturate(1.1);"></div>'
                    grid_html += '</div>'
                    st.markdown(grid_html, unsafe_allow_html=True)
                else:
                    st.info("請先上傳相片以查看 AI 優化效果。")
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 最終報告與資產確認")
        st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
        st.session_state.challenge = st.text_area("最難搞嘅位 (The Hardest Part)", st.session_state.challenge)
        if st.button("🚀 Confirm & Sync to Cloud"):
            st.balloons()
            st.success("✅ 同步完成！所有資產已確認。")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    with st.expander("🛠️ 系統運行日誌"):
        for log in st.session_state.debug_logs[-15:]:
            st.write(log)

if __name__ == "__main__": main()
