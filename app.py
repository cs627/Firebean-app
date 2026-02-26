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

# --- 1. 核心配置 (根據規格說明書 v2.5) ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

# 強制 AI 遵循 JSON 字典格式
FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Lead PR Strategist. Identity: 'Institutional Cool'. 
Language: Traditional Chinese (繁體中文).
Task: Transform diagnostic data into a professional PR strategy. 

CRITICAL RULE: Always return a single JSON OBJECT (not a list). 
Required keys: 
- "challenge_summary": (str)
- "solution_summary": (str)
- "1_google_slide": (str)
- "2_facebook_post": (str)
- "3_threads_post": (str)
- "4_instagram_post": (str, <150 chars)
- "5_linkedin_post": (str)
- "6_website": {"en": str, "tc": str, "jp": str}
"""

# --- 2. 核心邏輯與安全性防禦 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    """具備 JSON 強制提取與自動修復機制的 SDK 調用"""
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
        
        response = model.generate_content(contents, generation_config={
            "response_mime_type": "application/json" if is_json else "text/plain",
            "temperature": 0.2
        })
        
        if response and response.text:
            text = response.text.strip()
            if not is_json: return text
            
            # 使用 Regex 提取第一個 JSON 區塊
            match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
            json_str = match.group(0) if match else text
            
            # 🚀 格式防禦：如果 AI 回傳咗 List，強制轉返做 Dict
            data = json.loads(json_str)
            if isinstance(data, list) and len(data) > 0:
                log_debug("⚠️ AI 回傳咗 List 格式，正在自動修正為 Dictionary...", "warning")
                if isinstance(data[0], dict): return json.dumps(data[0])
            
            return json_str
    except Exception as e:
        log_debug(f"AI SDK Error: {str(e)[:100]}", "warning")
    return None

def init_session_state():
    """防禦性初始化：預防所有 AttributeError"""
    fields = {
        "active_tab": "📝 Project Collector",
        "client_name": "", "project_name": "", "venue": "", "youtube_link": "",
        "who_we_help": [WHO_WE_HELP_OPTIONS[0]], "what_we_do": [], "scope_of_work": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", 
        "challenge": "", "solution": "", "visual_facts": "", "hero_index": 0
    }
    for k, v in fields.items():
        if k not in st.session_state:
            st.session_state[k] = v

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    d = ImageDraw.Draw(img)
    d.text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def fill_dummy_data():
    """🚀 老細一鍵填充：完全遵循 PDF 專業內容與 SOW 邏輯"""
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = "2026 全功能數據對位測試"
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.youtube_link = "https://youtube.com/firebean_sync_demo"
    st.session_state.who_we_help = ["LIFESTYLE & CONSUMER"]
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope_of_work = ["Theme Design", "Event Production", "Concept Development"]
    # 填充高質量專業文案 (PDF Page 6)
    st.session_state.open_question_ans = "將20個通用診斷問題及其抽象答案,轉化為一套連貫、引人入勝且可操作的跨平台溝通策略,以有效傳達複雜的診斷洞察。"
    
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    
    st.session_state.mc_questions = [{"id": i+1, "question": f"指標維度 {i+1}？", "options": ["戰略優化", "維持"]} for i in range(20)]
    for i in range(1, 21):
        st.session_state[f"ans_{i}"] = ["戰略優化"]
    
    logo_buf = create_dummy_image("#FFFFFF", "LOGO")
    logo_b64 = base64.b64encode(logo_buf.getvalue()).decode()
    st.session_state.logo_black = logo_b64
    st.session_state.logo_white = logo_b64
    log_debug("🚀 高質量數據填充完成。", "success")

# --- 3. UI 元件 ---

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""<div style='display: flex; justify-content: flex-end;'><div style='position: relative; width: 110px; height: 110px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;'><svg width='110' height='110'><circle stroke='#d1d9e6' stroke-width='8' fill='transparent' r='45' cx='55' cy='55'/><circle stroke='#FF0000' stroke-width='8' stroke-dasharray='{circum}' stroke-dashoffset='{offset}' stroke-linecap='round' fill='transparent' r='45' cx='55' cy='55' style='transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;'/></svg><div style='position: absolute; font-size: 20px; font-weight: 900; color: #2D3436;'>{percent}%</div></div></div>"""

def apply_styles():
    st.markdown("""<style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 20px; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; padding: 25px; margin-bottom: 20px; }
        .mc-question { font-weight: 700; color: #FF0000 !important; margin-top: 15px; border-left: 4px solid #FF0000; padding-left: 10px; }
        .debug-terminal { background: #1E1E1E !important; color: #00FF00 !important; padding: 15px; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px; }
    </style>""", unsafe_allow_html=True)

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 10 維度進度計算
    score_items = ["client_name", "project_name", "venue", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.who_we_help else 0)
    filled += (1 if st.session_state.what_we_do else 0)
    filled += (1 if st.session_state.scope_of_work else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    mc_done = sum([1 for i in range(1, 21) if st.session_state.get(f"ans_{i}")])
    filled += (1 if mc_done == 20 else 0)
    
    percent = min(100, int((filled / 10) * 100))

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=160)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    # 🎯 100% Drive Logic
    if percent == 100 and st.session_state.active_tab == "📝 Project Collector":
        st.toast("🎯 100% 完成！正在自動跳轉至同步頁面..."); time.sleep(1.2)
        st.session_state.active_tab = "📋 Review & Multi-Sync"; st.rerun()

    tabs = st.tabs(["📝 Project Collector", "📋 Review & Multi-Sync", "🛠️ Debug Terminal"])

    # --- TAB 1: COLLECTOR ---
    with tabs[0]:
        if st.button("🧪 老細一鍵填充 (深度測試)", use_container_width=True): fill_dummy_data(); st.rerun()
        
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Black Logo", type=['png'], key="l_b")
            if ub: st.session_state.logo_black = base64.b64encode(ub.read()).decode()
        with col2:
            uw = st.file_uploader("White Logo", type=['png'], key="l_w")
            if uw: st.session_state.logo_white = base64.b64encode(uw.read()).decode()

        b1, b2, b3, b4 = st.columns(4)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b4.text_input("YouTube Link", st.session_state.youtube_link)

        ca, cb, cc = st.columns(3)
        with ca: st.session_state.who_we_help = [st.radio("Who we help", WHO_WE_HELP_OPTIONS)]
        with cb: st.session_state.what_we_do = [o for o in WHAT_WE_DO_OPTIONS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.what_we_do))]
        with cc: st.session_state.scope_of_work = [o for o in SOW_OPTIONS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.scope_of_work))]
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("🪄 生成 20 題繁中診斷題目"):
            res = call_gemini_sdk("Generate 20 MC diagnostic questions.", is_json=True)
            if res:
                try: st.session_state.mc_questions = json.loads(res); st.rerun()
                except: log_debug("JSON Parse Error", "error")

        if st.session_state.mc_questions:
            for q in st.session_state.mc_questions:
                st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                ans_key = f"ans_{q['id']}"
                st.session_state[ans_key] = st.multiselect("答案", q['options'], key=f"sel_{q['id']}", default=st.session_state.get(ans_key, []))
            st.session_state.open_question_ans = st.text_area("最核心的概念？", st.session_state.open_question_ans)
        
        f_up = st.file_uploader("Upload Photos", accept_multiple_files=True)
        if f_up: st.session_state.project_photos = f_up

    # --- TAB 2: REVIEW & SYNC ---
    with tabs[1]:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("🪄 生成六大平台及雙頁策略文案"):
            with st.spinner("AI Strategist 正在構思文案..."):
                mc_sum = [f"Q:{q['question']} A:{st.session_state.get(f'ans_{q['id']}')}" for q in st.session_state.mc_questions]
                prompt = f"數據對位: {st.session_state.project_name}. {mc_sum}. Return JSON for 6 platforms."
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    try:
                        data = json.loads(res)
                        # 🚀 規格書 5.1：字典格式安全門檻
                        if isinstance(data, dict):
                            st.session_state.ai_content = data
                            st.session_state.challenge = data.get("challenge_summary", "尚未定義挑戰")
                            st.session_state.solution = data.get("solution_summary", "尚未定義解決方案")
                            st.success("✅ 策略生成完成")
                        else: st.error("🚨 AI 回傳格式不符合預期 (非字典格式)")
                    except Exception as e: st.error(f"解析失敗: {str(e)}")

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync (Sheet + Slide Page 1 & 2)", type="primary", use_container_width=True):
                with st.spinner("🔄 多軌同步中..."):
                    try:
                        imgs = [base64.b64encode(f.read() if hasattr(f, "read") else f.getvalue()).decode() for f in st.session_state.project_photos]
                        # 🚀 數據完整性 Payload (完全對位規格書 Section 3 & 4)
                        payload = {
                            "action": "sync_project",
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue,
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "youtube": st.session_state.youtube_link,
                            "category": st.session_state.who_we_help[0],
                            "scope": ", ".join(st.session_state.scope_of_work),
                            "challenge": st.session_state.challenge,
                            "solution": st.session_state.solution,
                            "logo_white": st.session_state.logo_white, # 同步至 Slide
                            "logo_black": st.session_state.logo_black, # 同步至 Folder
                            "images": imgs,
                            "ai_content": st.session_state.ai_content
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sync Result: Sheet {r1.status_code}, Slide {r2.status_code}", "success")
                        st.balloons(); st.success("✅ 全部數據同步成功！")
                    except Exception as e: log_debug(f"Sync Fail: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 3: DEBUG ---
    with tabs[2]:
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__": main()
