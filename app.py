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
You are 'Firebean Brain', the Lead PR Strategist. Identity: 'Institutional Cool'. 
Language: Traditional Chinese (繁體中文).
Task: Transform diagnostic data into a professional PR strategy. 

OUTPUT FORMAT: Return a single valid JSON OBJECT with these keys:
- "challenge_summary": Brief summary of hurdles.
- "solution_summary": Core strategic approach.
- "1_google_slide": Structured professional points.
- "2_facebook_post": Warm, story-based.
- "3_threads_post": Humorous, critical, meme-potential.
- "4_instagram_post": Visual focus, emoji-rich, MUST BE < 150 words.
- "5_linkedin_post": Professional B2B, ROI focused.
- "6_website": {"en": "...", "tc": "...", "jp": "..."}
"""

# --- 2. 核心邏輯與安全性防禦 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    """具備規格書 5.1 節格式自動修復機制 (Format Fixer) 的 SDK 調用"""
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key:
        log_debug("🚨 找不到 API Key，請檢查 Streamlit Secrets。", "error")
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
            
            # 正則表達式提取 JSON 區塊
            match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
            json_str = match.group(0) if match else text
            
            # 🚀 v2.6 格式修復邏輯 (Format Fixer)
            try:
                data = json.loads(json_str)
                if isinstance(data, list) and len(data) > 0:
                    log_debug("⚠️ AI 回傳了 List，已自動提取第一個元素進行修復。", "warning")
                    if isinstance(data[0], dict): return json.dumps(data[0])
                return json_str
            except:
                return json_str
    except Exception as e:
        log_debug(f"AI SDK 錯誤: {str(e)[:100]}", "warning")
    return None

def init_session_state():
    """規格書 5.2 節：強制初始化所有變量"""
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
    """🚀 老細測試神器 (規格書第 9 節)：帶入 PDF 深度文案與 SOW"""
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = "2026 全自動數據對位測試"
    st.session_state.venue = "香港會議展覽中心 Hall 3G"
    st.session_state.youtube_link = "https://youtube.com/firebean_sync_demo"
    st.session_state.who_we_help = ["LIFESTYLE & CONSUMER"]
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope_of_work = ["Theme Design", "Event Production", "Concept Development"]
    
    # 填充 PDF 第 6 頁高品質文案
    st.session_state.open_question_ans = (
        "將20個通用診斷問題及其抽象答案,轉化為一套連貫、引人入勝且可操作的跨平台溝通策略, "
        "以有效傳達複雜的診斷洞察,確保受眾理解、參與並採取行動,同時維護品牌專業形象。"
    )
    
    # 生成 8 張彩色圖片以供雙頁分流測試
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"Dummy Photo {i+1}") for i, c in enumerate(colors)]
    
    # 填充 20 題 MC
    st.session_state.mc_questions = [{"id": i+1, "question": f"診斷指標維度 {i+1}？", "options": ["戰略優化", "維持現狀"]} for i in range(20)]
    for i in range(1, 21):
        st.session_state[f"ans_{i}"] = ["戰略優化"]
    
    # 模擬實體 Logo
    logo_buf = create_dummy_image("#FFFFFF", "FIREBEAN LOGO")
    logo_b64 = base64.b64encode(logo_buf.getvalue()).decode()
    st.session_state.logo_black = logo_b64
    st.session_state.logo_white = logo_b64
    log_debug("🚀 高質量 Dummy 數據填充完成，進度將達 100%。", "success")

# --- 3. UI 元件 (Institutional Cool Style) ---

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style='display: flex; justify-content: flex-end;'>
        <div style='position: relative; width: 110px; height: 110px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;'>
            <svg width='110' height='110'>
                <circle stroke='#d1d9e6' stroke-width='8' fill='transparent' r='45' cx='55' cy='55'/>
                <circle stroke='#FF0000' stroke-width='8' stroke-dasharray='{circum}' stroke-dashoffset='{offset}' stroke-linecap='round' fill='transparent' r='45' cx='55' cy='55' style='transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;'/>
            </svg>
            <div style='position: absolute; font-size: 20px; font-weight: 900; color: #2D3436;'>{percent}%</div>
        </div>
    </div>"""

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
        .debug-terminal { background: #1E1E1E !important; color: #00FF00 !important; padding: 15px; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px; }
    </style>""", unsafe_allow_html=True)

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 進度計算 (規格書 5.3 節：11 個維度計分)
    score_items = ["client_name", "project_name", "venue", "youtube_link", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.who_we_help else 0)
    filled += (1 if st.session_state.what_we_do else 0)
    filled += (1 if st.session_state.scope_of_work else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    mc_done = sum([1 for i in range(1, 21) if st.session_state.get(f"ans_{i}")])
    filled += (1 if mc_done == 20 else 0)
    
    percent = min(100, int((filled / 11) * 100))

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=160)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    # 🎯 規格書 5.3 節：100% Drive Logic 自動導向
    if percent == 100 and st.session_state.active_tab == "📝 Project Collector":
        st.toast("🎯 100% 完成！正在自動導向至 Review 頁面..."); time.sleep(1.2)
        st.session_state.active_tab = "📋 Review & Multi-Sync"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    nav_cols = st.columns(3)
    tab_list = ["📝 Project Collector", "📋 Review & Multi-Sync", "🛠️ Debug Terminal"]
    for i, t in enumerate(tab_list):
        if nav_cols[i].button(t, use_container_width=True, type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t; st.rerun()
    st.markdown("---")

    # --- TAB 1: COLLECTOR ---
    if st.session_state.active_tab == "📝 Project Collector":
        if st.button("🧪 老細一鍵填充 (規格書第 9 節測試)", use_container_width=True):
            fill_dummy_data(); st.rerun()
        
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Assets & Core Information")
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
        st.session_state.youtube_link = b4.text_input("YouTube Link", st.session_state.youtube_link)

        ca, cb, cc = st.columns(3)
        with ca: 
            st.markdown("**👥 Who we help (Category)**")
            st.session_state.who_we_help = [st.radio("Who we help", WHO_WE_HELP_OPTIONS, label_visibility="collapsed")]
        with cb: 
            st.markdown("**🚀 What we do**")
            st.session_state.what_we_do = [o for o in WHAT_WE_DO_OPTIONS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.what_we_do))]
        with cc: 
            st.markdown("**🛠️ SOW (Scope of Work)**")
            st.session_state.scope_of_work = [o for o in SOW_OPTIONS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.scope_of_work))]
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🧠 診斷思維出題 (Gemini 2.5)")
            if st.button("🪄 生成 20 條繁中診斷題目 (遵循 PR 維度)"):
                if not st.session_state.project_photos: st.error("請先上傳相片。")
                else:
                    loader = st.empty()
                    for p in range(0, 95, 5):
                        loader.markdown(get_animated_bar_html(p, "📸 正在掃描空間心理與溝通事實..."), unsafe_allow_html=True)
                        time.sleep(0.04)
                    
                    st.session_state.visual_facts = call_gemini_sdk("Extract visual facts from these photos.", image_files=st.session_state.project_photos)
                    prompt = f"基於視覺事實: {st.session_state.visual_facts}，為專案 {st.session_state.project_name} 生成 20 條繁中 MC 診斷題目。格式: [{{\"id\":1,\"question\":\"...\",\"options\":[\"A\",\"B\"]}}]"
                    res = call_gemini_sdk(prompt, is_json=True)
                    if res:
                        try:
                            st.session_state.mc_questions = json.loads(res)
                            loader.markdown(get_animated_bar_html(100, "✅ 診斷完成！"), unsafe_allow_html=True)
                            time.sleep(0.5); loader.empty()
                            st.rerun()
                        except: log_debug("JSON 解析錯誤", "error")

            if st.session_state.mc_questions:
                for q in st.session_state.mc_questions:
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                    ans_key = f"ans_{q['id']}"
                    st.session_state[ans_key] = st.multiselect("答案", q['options'], key=f"sel_{q['id']}", default=st.session_state.get(ans_key, []))
                st.session_state.open_question_ans = st.text_area("最核心的概念？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Require 4-8 Photos)")
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
        if st.button("🪄 生成六大平台文案 (遵循語文守則)"):
            with st.spinner("AI Strategist 正在根據 PR 專業維度對位數據..."):
                mc_sum = [f"Q:{q['question']} A:{st.session_state.get(f'ans_{q['id']}')}" for q in st.session_state.mc_questions]
                prompt = f"數據對位分析: {st.session_state.project_name}. 回答: {mc_sum}. 請根據規格書生成 6 個平台的繁中 JSON。IG 嚴格少於 150 字。"
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    try:
                        data = json.loads(res)
                        # 🚀 規格書 5.1 節：格式驗證
                        if isinstance(data, dict):
                            st.session_state.ai_content = data
                            st.session_state.challenge = data.get("challenge_summary", "尚未定義挑戰")
                            st.session_state.solution = data.get("solution_summary", "尚未定義解決方案")
                            st.success("✅ 文案對位生成完成")
                        else: st.error("AI 回傳格式不正確 (非 Dictionary)")
                    except Exception as e: st.error(f"解析失敗: {str(e)}")

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync (Sheet + Slide + Folder)", type="primary", use_container_width=True):
                with st.spinner("🔄 多軌同步中..."):
                    try:
                        imgs = [base64.b64encode(f.read() if hasattr(f, "read") else f.getvalue()).decode() for f in st.session_state.project_photos]
                        # 🚀 規格書第 6 & 7 節：Payload 全對位
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
                            "logo_white": st.session_state.logo_white, # 同步至 Slide 做實體替換
                            "logo_black": st.session_state.logo_black, # 同步至 Folder
                            "images": imgs,
                            "ai_content": st.session_state.ai_content
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sync Result: Sheet {r1.status_code}, Slide {r2.status_code}", "success")
                        st.balloons(); st.success("✅ 全部數據同步對位成功！")
                    except Exception as e: log_debug(f"Sync Fail: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 3: DEBUG ---
    elif st.session_state.active_tab == "🛠️ Debug Terminal":
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
