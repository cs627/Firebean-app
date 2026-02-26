import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageEnhance, ImageOps, ImageDraw
from datetime import datetime

# --- 1. 核心配置 (根據規格說明書 Section 2) ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"

# 🚀 鎖定穩定版模型 ID
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Lead PR Strategist. Identity: 'Institutional Cool'. 
Language: Traditional Chinese.
Focus: Transform diagnostic insights into a coherent, engaging cross-platform strategy.
Ensure Instagram content is strictly < 150 chars.
"""

# --- 2. 核心邏輯 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key:
        log_debug("🚨 找不到 API Key", "error")
        return None
    try:
        genai.configure(api_key=secret_key)
        model = genai.GenerativeModel(model_name=STABLE_MODEL_ID, system_instruction=FIREBEAN_SYSTEM_PROMPT)
        contents = [prompt]
        if image_files:
            for f in image_files:
                img = Image.open(f)
                img.thumbnail((800, 800))
                contents.append(img)
        response = model.generate_content(contents, generation_config={"response_mime_type": "application/json" if is_json else "text/plain", "temperature": 0.3})
        if response and response.text:
            cleaned = response.text.strip()
            if not is_json: return cleaned
            match = re.search(r'(\[.*\]|\{.*\})', cleaned, re.DOTALL)
            return match.group(1) if match else cleaned
    except Exception as e:
        log_debug(f"AI Error: {str(e)[:50]}", "warning")
    return None

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    d = ImageDraw.Draw(img)
    d.text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def fill_dummy_data():
    """🚀 老細一鍵填充：實現深度 Dummy 內容及 8 張相片"""
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = "2026 全功能數據對齊測試"
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.youtube_link = "https://youtube.com/firebean_sync_demo"
    st.session_state.who_we_help = ["LIFESTYLE & CONSUMER"]
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope_of_word = ["Theme Design", "Event Production", "Concept Development"]
    st.session_state.open_question_ans = "將20個通用診斷問題及其抽象答案,轉化為一套連貫、引人入勝且可操作的跨平台溝通策略。"
    
    # 生 8 張彩色圖片測試雙頁分流
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"Dummy Photo {i+1}") for i, c in enumerate(colors)]
    
    # 填 20 題 MC
    st.session_state.mc_questions = [{"id": i+1, "question": f"診斷指標 {i+1} 測試題目？", "options": ["選項 A", "選項 B"]} for i in range(20)]
    for i in range(1, 21):
        st.session_state[f"ans_{i}"] = ["選項 A"]
    
    # 繪製模擬 Logo
    logo_buf = create_dummy_image("#FFFFFF", "FIREBEAN LOGO")
    logo_b64 = base64.b64encode(logo_buf.getvalue()).decode()
    st.session_state.logo_black = logo_b64
    st.session_state.logo_white = logo_b64
    log_debug("🚀 高質量數據填充完成，觸發自動導向。", "success")

def init_session_state():
    """修復 AttributeError：強制初始化所有關鍵變量"""
    fields = {
        "active_tab": "📝 Project Collector",
        "client_name": "", "project_name": "", "venue": "", "youtube_link": "",
        "who_we_help": [WHO_WE_HELP_OPTIONS[0]], "what_we_do": [], "scope_of_word": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", 
        "challenge": "", "solution": "", "visual_facts": ""
    }
    for k, v in fields.items():
        if k not in st.session_state:
            st.session_state[k] = v

# --- 3. UI 組件 ---

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""<div style='display: flex; justify-content: flex-end;'><div style='position: relative; width: 110px; height: 110px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;'><svg width='110' height='110'><circle stroke='#d1d9e6' stroke-width='8' fill='transparent' r='45' cx='55' cy='55'/><circle stroke='#FF0000' stroke-width='8' stroke-dasharray='{circum}' stroke-dashoffset='{offset}' stroke-linecap='round' fill='transparent' r='45' cx='55' cy='55' style='transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;'/></svg><div style='position: absolute; font-size: 20px; font-weight: 900; color: #2D3436;'>{percent}%</div></div></div>"""

def get_animated_bar_html(percent, status_text):
    return f"""
    <div style="padding: 25px; background: #E0E5EC; border-radius: 15px; box-shadow: inset 6px 6px 12px #bec3c9, inset -6px -6px 12px #ffffff; margin: 20px 0;">
        <div style="font-weight: 800; color: #FF0000; font-size: 14px; text-align: center; margin-bottom: 10px;">{status_text}</div>
        <div style="width: 100%; background: #d1d9e6; border-radius: 50px; height: 18px; position: relative; overflow: hidden; box-shadow: inset 4px 4px 8px #bec3c9;">
            <div style="width: {percent}%; background: linear-gradient(90deg, #FF0000, #b30000); height: 100%; border-radius: 50px; transition: width 0.4s ease-out;"></div>
        </div>
        <div style="text-align: right; font-size: 11px; font-weight: 900; margin-top: 5px;">{percent}%</div>
    </div>"""

def apply_styles():
    st.markdown("""<style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 20px; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; padding: 25px; margin-bottom: 20px; }
        .mc-question { font-weight: 700; color: #FF0000 !important; margin-top: 15px; border-left: 4px solid #FF0000; padding-left: 10px; }
    </style>""", unsafe_allow_html=True)

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 進度計算 (10 維度)
    score_items = ["client_name", "project_name", "venue", "youtube_link", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.who_we_help else 0)
    filled += (1 if st.session_state.what_we_do else 0)
    filled += (1 if st.session_state.scope_of_word else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    mc_count = sum([1 for i in range(1, 21) if st.session_state.get(f"ans_{i}")])
    filled += (1 if mc_count == 20 else 0)
    
    percent = min(100, int((filled / 10) * 100))

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=160)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    # 🎯 自動導向邏輯 (100% Drive Logic)
    if percent == 100 and st.session_state.active_tab == "📝 Project Collector":
        st.toast("🎯 100% 完成！正在自動跳轉至同步頁面...")
        time.sleep(1.2)
        st.session_state.active_tab = "📋 Review & Multi-Sync"
        st.rerun()

    # 導航
    st.markdown("<br>", unsafe_allow_html=True)
    n_cols = st.columns(3)
    tab_list = ["📝 Project Collector", "📋 Review & Multi-Sync", "👥 CRM & Contacts"]
    for i, t in enumerate(tab_list):
        if n_cols[i].button(t, use_container_width=True, type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t
            st.rerun()
    st.markdown("---")

    # --- TAB 1: COLLECTOR ---
    if st.session_state.active_tab == "📝 Project Collector":
        if st.button("🧪 老細一鍵填充 (測試 100% 自動跳轉)", use_container_width=True):
            fill_dummy_data()
            st.rerun()
        
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Assets & Fact Info")
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Upload Black Logo", type=['png'], key="l_b")
            if ub: st.session_state.logo_black = base64.b64encode(ub.read()).decode()
        with col2:
            uw = st.file_uploader("Upload White Logo", type=['png'], key="l_w")
            if uw: st.session_state.logo_white = base64.b64encode(uw.read()).decode()
        
        b1, b2, b3, b4 = st.columns(4)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b4.text_input("YouTube", st.session_state.youtube_link)

        c_a, c_b, c_c = st.columns(3)
        with c_a: 
            st.markdown("**👥 Category**")
            st.session_state.who_we_help = [st.radio("Cat", WHO_WE_HELP_OPTIONS, label_visibility="collapsed")]
        with c_b: 
            st.markdown("**🚀 What we do**")
            st.session_state.what_we_do = [o for o in WHAT_WE_DO_OPTIONS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.what_we_do))]
        with c_c:
            st.markdown("**🛠️ SOW (Scope of Work)**")
            st.session_state.scope_of_word = [o for o in SOW_OPTIONS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.scope_of_word))]
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🧠 診斷思維出題 (Gemini 2.5)")
            if st.button("🪄 生成 20 條繁中診斷題目"):
                if not st.session_state.project_photos: st.error("請先上傳相片。")
                else:
                    loader = st.empty()
                    for p in range(0, 95, 5):
                        loader.markdown(get_animated_bar_html(p, "📸 正在掃描空間與 Branding 事實..."), unsafe_allow_html=True)
                        time.sleep(0.04)
                    
                    st.session_state.visual_facts = call_gemini_sdk("Extract visual facts from these photos.", image_files=st.session_state.project_photos)
                    prompt = f"基於事實 {st.session_state.visual_facts} 生成 20 條繁中 MC 題目。格式: [{{\"id\":1,\"question\":\"...\",\"options\":[\"A\",\"B\"]}}]"
                    res = call_gemini_sdk(prompt, is_json=True)
                    if res:
                        st.session_state.mc_questions = json.loads(res)
                        loader.markdown(get_animated_bar_html(100, "✅ 診斷完成！"), unsafe_allow_html=True)
                        time.sleep(0.5); loader.empty()

            if st.session_state.mc_questions:
                for q in st.session_state.mc_questions:
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                    ans_key = f"ans_{q['id']}"
                    st.session_state[ans_key] = st.multiselect("答案", q['options'], key=f"sel_{q['id']}", default=st.session_state.get(ans_key, []))
                st.session_state.open_question_ans = st.text_area("最特別概念？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Require 4-8)")
            f_up = st.file_uploader("Upload Photos", accept_multiple_files=True)
            if f_up: st.session_state.project_photos = f_up
            if st.session_state.project_photos:
                g_cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with g_cols[i%4]:
                        try: st.image(Image.open(f), use_container_width=True)
                        except: st.image(f, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: REVIEW & SYNC ---
    elif st.session_state.active_tab == "📋 Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("🪄 生成六大平台對接文案 (Follow PR DNA)"):
            loader = st.empty()
            for p in range(0, 96, 4):
                loader.markdown(get_animated_bar_html(p, "🧠 AI Strategist 對位數據中..."), unsafe_allow_html=True)
                time.sleep(0.04)
            
            mc_sum = [f"Q:{q['question']} A:{st.session_state.get(f'ans_{q['id']}')}" for q in st.session_state.mc_questions]
            prompt = f"數據:{mc_sum}. Generate JSON for 6 platforms. Website needs EN/TC/JP. IG strictly <150 chars. Include 'challenge_summary' and 'solution_summary'."
            res = call_gemini_sdk(prompt, is_json=True)
            if res:
                st.session_state.ai_content = json.loads(res)
                st.session_state.challenge = st.session_state.ai_content.get("challenge_summary", "")
                st.session_state.solution = st.session_state.ai_content.get("solution_summary", "")
                loader.markdown(get_animated_bar_html(100, "✅ 對位成功！"), unsafe_allow_html=True)
                time.sleep(0.5); loader.empty()

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync (Sheet + Slide Page 1 & 2)", type="primary", use_container_width=True):
                with st.spinner("🔄 多軌同步中..."):
                    try:
                        imgs = []
                        for f in st.session_state.project_photos:
                            if hasattr(f, "seek"): f.seek(0)
                            imgs.append(base64.b64encode(f.read() if hasattr(f, "read") else f.getvalue()).decode())
                        
                        payload = {
                            "action": "sync_project",
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue,
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "category": st.session_state.who_we_help[0],
                            "scope": ", ".join(st.session_state.scope_of_word),
                            "challenge": st.session_state.challenge,
                            "solution": st.session_state.solution,
                            "logo_white": st.session_state.logo_white, # 同步白 Logo 到 Slide
                            "logo_black": st.session_state.logo_black, # 同步黑 Logo 到 Folder
                            "images": imgs,
                            "ai_content": st.session_state.ai_content
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sync Result: Sheet {r1.status_code}, Slide {r2.status_code}", "success")
                        st.balloons(); st.success("✅ 全部數據同步成功！")
                    except Exception as e: log_debug(f"Sync Fail: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Debug Terminal ---
    with st.expander("🛠️ Debug Terminal", expanded=True):
        if st.button("🔍 測試 API 連線"):
            res = call_gemini_sdk("Ping test.")
            if res: st.success("Gemini 2.5 Online")
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
