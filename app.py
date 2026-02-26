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

# --- 1. 核心配置 (根據規格說明書 v2.6) ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Lead PR Strategist, and an expert Chief Editor and B2B/B2C Journalist for a premium online magazine.
Task: Transform diagnostic data into a professional PR strategy JSON. 
Always return a valid JSON object with keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website.

**CRITICAL INSTRUCTION FOR '6_website'**: 
The '6_website' key MUST be a nested JSON object containing exactly four keys: "angle_chosen", "en", "tc", and "jp".
You must write a highly engaging, 500-word feature article based on the provided inputs for the website content.

To ensure a diverse content library, RANDOMLY SELECT ONLY ONE of the 5 writing styles/angles below. Do not mix styles:
1. The Thought Leadership Angle: Interpret the news. Frame the Pain Point as a systemic flaw and the Solution/Event as the visionary blueprint.
2. The Contrarian / Disruptor Angle: Start with a bold, counter-intuitive hook. Highlight how the Pain Point is caused by outdated thinking, and present the Solution/Event as the ultimate disruption.
3. The Human-Centric / Emotional Storytelling Angle: Focus on human frustration, burnout, or disconnection. Frame the Solution/Event as a return to authentic, meaningful human connection and relief.
4. The Analytical Problem-Solver: Explicitly break down the Pain Point, agitate the negative impact, and logically reveal the Solution/Event as the actionable cure.
5. The Insider / Behind-the-Scenes Angle: Write from an exclusive "fly-on-the-wall" perspective. Frame the Pain Point as a secret struggle, and the Event/Solution as the exclusive reveal.

Format & Structure Requirements for '6_website':
- Word Count: Approximately 500 words per language.
- Structure: Use engaging editorial Subtitles (H2/H3). Use short, punchy paragraphs.
- The Core Narrative: Seamlessly weave the [Basic Information], [Event Details], [Pain Point], and [Solution] into the chosen narrative angle.
- The Punch Line: The final paragraph before the FAQ must be a single, bolded, highly memorable concluding sentence.
- The Fast Recap FAQ: End the article with a quick, 3-question FAQ section summarizing the pain point, solution, and event details.

Language Output Requirement for '6_website':
- "angle_chosen": State the name of the angle you selected (e.g., "Style 2: The Contrarian").
- "en": English (Premium editorial tone)
- "tc": Traditional Chinese (Hong Kong localization, fluent and natural editorial style)
- "jp": Japanese (Polite, professional business-magazine tone - Desu/Masu form)

DO NOT output any conversational text outside the JSON object.
"""

# --- 2. 核心邏輯與安全性防禦 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    """規格書 5.1 節格式自動修復機制 (Format Fixer)"""
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
            
            # 正則提取 JSON
            match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
            json_str = match.group(0) if match else text
            
            # 🚀 v2.6 格式修復：如果是 List 則提取第一個 Dict
            try:
                data = json.loads(json_str)
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict): return json.dumps(data[0])
                return json_str
            except:
                return json_str
    except Exception as e:
        log_debug(f"AI SDK 錯誤: {str(e)[:50]}", "warning")
    return None

def init_session_state():
    """規格書 5.2 節：強制初始化所有變量"""
    fields = {
        "active_tab": "📝 Project Collector",
        "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": "2026", "event_month": "FEB",
        "category": WHO_WE_HELP_OPTIONS[0], "what_we_do": [], "scope": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", 
        "challenge": "", "solution": "", "visual_facts": ""
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
    """🚀 老細一鍵填充：帶入規格書第 6 節高品質文案"""
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = "2026 旗艦同步測試"
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.youtube = "https://youtube.com/firebean_sync_demo"
    st.session_state.category = "LIFESTYLE & CONSUMER"
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope = ["Theme Design", "Event Production", "Concept Development"]
    st.session_state.open_question_ans = "將 20 個通用診斷問題轉化為一套連貫、引人入勝且可操作的跨平台策略。"
    
    # 生成 8 張測試相
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    
    # 填充 20 題 MC
    st.session_state.mc_questions = [{"id": i+1, "question": f"診斷指標 {i+1}？", "options": ["戰略優化", "維持"]} for i in range(20)]
    for i in range(1, 21): st.session_state[f"ans_{i}"] = ["戰略優化"]
    
    # 模擬 Logo
    dummy_logo = base64.b64encode(create_dummy_image("#FFFFFF", "LOGO").getvalue()).decode()
    st.session_state.logo_black = dummy_logo
    st.session_state.logo_white = dummy_logo
    log_debug("🚀 高質量測試數據填充完成，進度將達 100%。", "success")

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

    # 11 維度進度計算 (規格書 5.3)
    score_items = ["client_name", "project_name", "venue", "youtube", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.category else 0)
    filled += (1 if st.session_state.what_we_do else 0)
    filled += (1 if st.session_state.scope else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    mc_done = sum([1 for i in range(1, 21) if st.session_state.get(f"ans_{i}")])
    filled += (1 if mc_done == 20 else 0)
    percent = min(100, int((filled / 11) * 100))

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=160)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    # 🎯 規格書 5.3：100% 自動跳轉至 Review 頁
    if percent == 100 and st.session_state.active_tab == "📝 Project Collector":
        st.toast("🎯 100% 完成！正在自動跳轉...")
        time.sleep(1.2)
        st.session_state.active_tab = "📋 Review & Multi-Sync"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    tab_list = ["📝 Project Collector", "📋 Review & Multi-Sync", "🛠️ Debug Terminal"]
    nav_cols = st.columns(3)
    for i, t in enumerate(tab_list):
        if nav_cols[i].button(t, use_container_width=True, type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t; st.rerun()

    # --- TAB 分頁內容 ---
    if st.session_state.active_tab == "📝 Project Collector":
        if st.button("🧪 老細一鍵填充 (深度內容測試)", use_container_width=True):
            fill_dummy_data(); st.rerun()
        
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
        st.session_state.youtube = b4.text_input("YouTube Link", st.session_state.youtube)

        ca, cb, cc = st.columns(3)
        with ca:
            st.session_state.category = st.radio("Who we help (Category)", WHO_WE_HELP_OPTIONS, index=WHO_WE_HELP_OPTIONS.index(st.session_state.category) if st.session_state.category in WHO_WE_HELP_OPTIONS else 0)
        with cb:
            st.session_state.what_we_do = [o for o in WHAT_WE_DO_OPTIONS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.what_we_do))]
        with cc:
            st.session_state.scope = [o for o in SOW_OPTIONS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.scope))]
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            if st.button("🪄 生成 20 題繁中診斷題目"):
                if not st.session_state.project_photos: st.error("請先上傳相片。")
                else:
                    with st.spinner("AI 掃描相片 Facts 中..."):
                        facts = call_gemini_sdk("Identify branding and tech facts.", image_files=st.session_state.project_photos)
                        res = call_gemini_sdk(f"基於事實 {facts} 生成 20 題 MC。格式: [{{\"id\":1,\"question\":\"...\",\"options\":[\"A\",\"B\"]}}]", is_json=True)
                        if res: st.session_state.mc_questions = json.loads(res); st.rerun()

            if st.session_state.mc_questions:
                for q in st.session_state.mc_questions:
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                    ans_key = f"ans_{q['id']}"
                    st.session_state[ans_key] = st.multiselect("答案", q['options'], key=f"sel_{q['id']}", default=st.session_state.get(ans_key, []))
                st.session_state.open_question_ans = st.text_area("最核心的概念？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            f_up = st.file_uploader("Upload 4-8 Photos", accept_multiple_files=True)
            if f_up: st.session_state.project_photos = f_up
            if st.session_state.project_photos:
                g_cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with g_cols[i%4]:
                        try: st.image(Image.open(f), use_container_width=True)
                        except: st.image(f, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.active_tab == "📋 Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("🪄 生成六大平台對接文案"):
            with st.spinner("AI Strategist 正在構思文案..."):
                mc_sum = [f"Q:{q['question']} A:{st.session_state.get(f'ans_{q['id']}')}" for q in st.session_state.mc_questions]
                prompt = f"""
分析專案: {st.session_state.project_name}. 生成 JSON。IG < 150 字。

【專案診斷核心數據 (Diagnostic Data)】
{mc_sum}

請嚴格根據以上診斷數據與以下專案基本資料，歸納出痛點與解決方案，並撰寫 6_website 的雜誌級文章與其他社群文案：
### Input Data:
- [Basic Information]: Client Name: {st.session_state.client_name}, Project Name: {st.session_state.project_name}, Category: {st.session_state.category}, Scope of Work: {", ".join(st.session_state.scope)}
- [Event Details]: Event Date: {st.session_state.event_year} {st.session_state.event_month}, Venue: {st.session_state.venue}, What we do: {", ".join(st.session_state.what_we_do)}
- [Pain Point]: (請依據診斷數據總結) 補充背景: {st.session_state.open_question_ans}
- [Solution]: (請依據診斷數據與活動形式總結) 相關影片參考: {st.session_state.youtube}
"""
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    data = json.loads(res)
                    if isinstance(data, dict):
                        st.session_state.ai_content = data
                        st.session_state.challenge = data.get("challenge_summary", "尚未生成")
                        st.session_state.solution = data.get("solution_summary", "尚未生成")
                        st.success("✅ 策略生成完成")

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync (Sheet + Slide + Drive)", type="primary", use_container_width=True):
                with st.spinner("🔄 同步中..."):
                    try:
                        imgs = [base64.b64encode(f.read() if hasattr(f, "read") else f.getvalue()).decode() for f in st.session_state.project_photos]
                        # 🚀 校準對位 Payload (對應規格書 Section 3 & 4)
                        payload = {
                            "action": "sync_project",
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue,
                            "date": f"{st.session_state.event_year} {st.session_state.event_month}",
                            "youtube": st.session_state.youtube,
                            "category": st.session_state.category, 
                            "category_what": ", ".join(st.session_state.what_we_do),
                            "scope": ", ".join(st.session_state.scope),       
                            "challenge": st.session_state.challenge,
                            "solution": st.session_state.solution,
                            "open_question": st.session_state.open_question_ans,
                            "logo_white": st.session_state.logo_white,
                            "logo_black": st.session_state.logo_black,
                            "images": imgs,
                            "ai_content": st.session_state.ai_content
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sync: Sheet {r1.status_code}, Slide {r2.status_code}", "success")
                        st.balloons(); st.success("✅ 全部數據同步對位成功！")
                    except Exception as e: log_debug(f"Sync Fail: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.active_tab == "🛠️ Debug Terminal":
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__": main()
