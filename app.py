import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import traceback
import requests
from PIL import Image, ImageEnhance, ImageOps
from datetime import datetime

# --- 1. 核心配置與 API / Webhook URL ---
# Master DB (Google Sheet) 接收器
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx6YNAjNNndamdkcULS71Q_qkkbclBViLlx9B8e7LaaxyapMc7jsgdvhMHZ3d_wLzXw/exec"
# Google Slide 自動生成接收器
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbya_pl6h99zY_LrURojCL86c20NwxdeW6V9bhCXqgPjJdz2NVPgeFThthcR6gfw0d1P/exec"

API_KEYS_POOL = [
    "AIzaSyA-5qXWjtzlUWP0IDMVUByMXdbylt8rTSA",
    "AIzaSyCVuoSuWV3tfGCu2tjikCkMOVRWCBFne20",
    "AIzaSyCZKtjLqN4FUQ76c3DYoDW20tTkFki_Rxk"
]

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
Motto: 'Turn Policy into Play'.
"""

# --- 2. 核心調試與官方 SDK 智能輪詢引擎 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False, dynamic_sys_prompt=None):
    secret_key = ""
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        secret_key = st.secrets["GEMINI_API_KEY"]
        
    all_keys = ([secret_key] if secret_key else []) + API_KEYS_POOL
    model_name = "gemini-2.5-flash"
    
    sys_instruction = dynamic_sys_prompt if dynamic_sys_prompt else FIREBEAN_SYSTEM_PROMPT

    for idx, key in enumerate(all_keys):
        try:
            is_secret = "(Secret Key)" if (secret_key and idx == 0) else f"(Pool Key #{idx})"
            log_debug(f"Attempting API with Key {is_secret}...", "info")
            genai.configure(api_key=key)
            
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json" if is_json else "text/plain"
            )
            
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=sys_instruction
            )
            
            contents = [prompt]
            if image_file:
                contents.append(image_file)
                
            response = model.generate_content(contents, generation_config=generation_config)
            
            if response and response.text:
                log_debug(f"✅ Success with Key {is_secret}!", "success")
                cleaned_text = response.text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                return cleaned_text.strip()
                
        except Exception as e:
            log_debug(f"Key Error {is_secret}: {str(e)}", "warning")
            continue
            
    log_debug("Critical Error: All API keys failed.", "error")
    return None

def test_api_connection():
    log_debug("🚀 Starting SDK Connection Test...", "info")
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        log_debug("🔑 [System] 成功讀取 Streamlit Secrets 中的 API Key！", "success")
    else:
        log_debug("⚠️ [System] 找不到 Streamlit Secrets！請檢查 Cloud Settings。", "error")
        
    res = call_gemini_sdk("Ping test. Please respond exactly with: 'Firebean 2.5 Online.'")
    if res:
        st.toast("✅ SDK 連線成功！Gemini 2.5 運作中。")
    else:
        st.toast("❌ 金鑰連線失敗，請檢查 Debug 欄", icon="🔥")

def standardize_logo(logo_file, target_size=(800, 400), padding=40):
    try:
        raw = Image.open(logo_file)
        img = ImageOps.exif_transpose(raw).convert("RGBA")
        bbox = img.getbbox()
        if bbox: img = img.crop(bbox)
        inner_w, inner_h = target_size[0] - (padding * 2), target_size[1] - (padding * 2)
        img.thumbnail((inner_w, inner_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, img)
        buf = io.BytesIO(); canvas.save(buf, format="PNG")
        log_debug(f"Logo '{logo_file.name}' normalized & converted to Base64 PNG.", "success")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log_debug(f"Logo Fix Error: {str(e)}", "error")
        return ""

def manna_ai_enhance(image_file):
    log_debug(f"Processing AI Vision for: {image_file.name}")
    with st.spinner("🚀 Manna AI 校正轉向並同步視角..."):
        try:
            raw_img = Image.open(image_file)
            img = ImageOps.exif_transpose(raw_img).convert("RGB")
            img_enhanced = ImageEnhance.Contrast(img).enhance(1.15)
            call_gemini_sdk("Analyze this institutional project photo.", image_file=img)
            return img_enhanced
        except Exception:
            return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

def generate_mc_questions():
    prompt = f"""
    You are an AI PR Strategist. The user is a PR agency employee (Account Executive) logging details about a recently completed campaign they executed for a CLIENT.
    They have inputted the following for this project:
    - Client Category: {st.session_state.who_we_help}
    - What We Do: {st.session_state.what_we_do}
    - Scope of Work: {st.session_state.scope_of_word}
    
    Please systematically generate exactly 20 multiple-choice questions (A/B/C/D) to extract the "soul" of this project.
    
    **CRITICAL REQUIREMENT 1: ALL questions and options MUST be written in Traditional Chinese (繁體中文).**
    **CRITICAL REQUIREMENT 2: 這些題目必須設計為「可多選 (Multiple-response)」的情境題，選項之間不應完全互斥，讓用戶可以勾選所有符合該專案情況的策略或痛點。**
    
    Logic (6-7-7 Matrix):
    - [6 Questions] about Client Category: 這是詢問「客戶/品牌」面對的痛點與商業目標，絕對不是問公關行業本身的痛點。請詢問該客戶的目標受眾遇到了什麼問題？客戶希望透過這次活動改變大眾什麼觀感？
    - [7 Questions] about What We Do: 詢問關於該活動的體驗設計、互動科技應用及靈魂定位。
    - [7 Questions] about Scope of Work: 詢問關於具體的公關執行策略、宣傳風格及落地成效。
    
    Output strictly as a JSON array of objects. Example format:
    [
        {{"id": 1, "category": "客戶品牌痛點 (Client Category)", "question": "這是一條詢問客戶痛點的繁體中文問題...", "options": ["A. 選項一", "B. 選項二", "C. 選項三", "D. 選項四"]}}
    ]
    Do not wrap in Markdown. Output JSON only.
    """
    res = call_gemini_sdk(prompt, is_json=True)
    if res:
        try:
            questions = json.loads(res)
            st.session_state.mc_questions = questions
            return True
        except:
            log_debug("Failed to parse MC JSON.", "error")
            return False
    return False

# --- 3. UI 樣式與狀態管理 ---

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        
        /* 強制深色文字與白底輸入框，避免 Dark Mode 影響閱讀 */
        h1, h2, h3, h4, h5, h6, p, label, div[data-testid="stMarkdownContainer"] > p { color: #2D3436 !important; }
        input, textarea, div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #2D3436 !important; -webkit-text-fill-color: #2D3436 !important; }
        
        div[data-testid="stCheckbox"] label span { color: #2D3436 !important; }
        div[data-testid="stRadio"] label span { color: #2D3436 !important; }

        .neu-card { background: #E0E5EC; border-radius: 25px; box-shadow: 12px 12px 24px #bec3c9, -12px -12px 24px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.4); border-radius: 12px; }
        .ai-status-tag { background: #FF3333; color: white !important; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 800; display: inline-block; margin-bottom: 5px; }
        
        .debug-terminal { background: #1E1E1E !important; color: #00FF00 !important; padding: 12px; font-family: 'Courier New', monospace; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px 10px 0 0; max-height: 250px; overflow-y: auto; margin-top: 50px; }
        .debug-terminal p, .debug-terminal span, .debug-terminal div { color: inherit !important; background: transparent !important;}
        .debug-success { color: #00FF00 !important; font-weight: bold; }
        .debug-error { color: #FF5555 !important; font-weight: bold; }
        
        .blocker-alert { background-color: #ffe6e6 !important; border-left: 5px solid #FF0000; padding: 15px; border-radius: 5px; margin-bottom: 15px; color: #2D3436 !important;}
        .mc-question { font-weight: 600; color: #d32f2f !important; margin-top: 15px; }
        .mc-hint { font-size: 0.8em; color: #666; font-weight: normal; }
        </style>
    """, unsafe_allow_html=True)

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 130px; height: 130px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="130" height="130"><circle stroke="#d1d9e6" stroke-width="10" fill="transparent" r="55" cx="65" cy="65"/><circle stroke="#FF0000" stroke-width="10" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="55" cx="65" cy="65" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg>
            <div style="position: absolute; font-size: 26px; font-weight: 900; color: #2D3436;">{percent}%</div>
        </div>
    </div>
    """

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "who_we_help": [WHO_WE_HELP_OPTIONS[0]], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "",
        "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": [],
        "mc_questions": [], "open_question_ans": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# --- 4. Main App 邏輯 ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    score_items = ["client_name", "project_name", "venue", "open_question_ans"]
    filled = sum([1 for f in score_items if st.session_state.get(f)])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0)
    filled += (1 if len(st.session_state.mc_questions) == 20 else 0)
    
    percent = int((filled / 10) * 100)
    if percent > 100: percent = 100

    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector & 20 MC Matrix", "📋 AI Review & 6 Platforms Sync"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Logos (Must upload Black or White)")
        lc1, lc2 = st.columns(2)
        with lc1:
            ub = st.file_uploader("Upload Black Logo", type=['png'], key="logo_b")
            if ub and st.button("📏 Fix Black"): st.session_state.logo_black = standardize_logo(ub)
        with lc2:
            uw = st.file_uploader("Upload White Logo", type=['png'], key="logo_w")
            if uw and st.button("📏 Fix White"): st.session_state.logo_white = standardize_logo(uw)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Core Information")
        b1, b2, b3_y, b3_m, b4, b5 = st.columns([1, 1, 0.5, 0.4, 1, 1])
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("Year", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("Month", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.venue = b4.text_input("Venue", st.session_state.venue)
        st.session_state.youtube_link = b5.text_input("YouTube Link (Optional)", st.session_state.youtube_link)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🗂️ Project Classification")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("**👥 Category (Client)** *(單選)*")
            cat_idx = WHO_WE_HELP_OPTIONS.index(st.session_state.who_we_help[0]) if st.session_state.who_we_help and st.session_state.who_we_help[0] in WHO_WE_HELP_OPTIONS else 0
            selected_cat = st.radio("Category", WHO_WE_HELP_OPTIONS, index=cat_idx, label_visibility="collapsed")
            st.session_state.who_we_help = [selected_cat]
            
        with c2:
            st.markdown("**🚀 What we do** *(多選)*")
            new_what_we_do = []
            for opt in WHAT_WE_DO_OPTIONS:
                if st.checkbox(opt, value=(opt in st.session_state.what_we_do), key=f"what_{opt}"):
                    new_what_we_do.append(opt)
            st.session_state.what_we_do = new_what_we_do
            
        with c3:
            st.markdown("**🛠️ Scope of Work** *(多選)*")
            new_sow = []
            for opt in SOW_OPTIONS:
                if st.checkbox(opt, value=(opt in st.session_state.scope_of_word), key=f"sow_{opt}"):
                    new_sow.append(opt)
            st.session_state.scope_of_word = new_sow
            
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🧠 專案靈魂萃取器 (6-7-7 Matrix)")
            
            if st.button("🪄 生成 20 條專案靈魂測驗題"):
                if not st.session_state.who_we_help or not st.session_state.what_we_do or not st.session_state.scope_of_word:
                    st.error("請先勾選 Category, What we do, 以及 Scope of Work！")
                else:
                    with st.spinner("AI 正在根據你的設定生成 20 條針對性題目 (繁體中文)..."):
                        success = generate_mc_questions()
                        if success:
                            st.success("✅ 題目已生成！請勾選符合情況的選項 (可多選)。")
                        else:
                            st.error("生成失敗，請重試。")

            if st.session_state.mc_questions:
                st.markdown("---")
                for q in st.session_state.mc_questions:
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. [{q['category']}] {q['question']} <span class='mc-hint'>(可多選)</span></div>", unsafe_allow_html=True)
                    
                    selected_opts = []
                    for opt_idx, opt in enumerate(q['options']):
                        if st.checkbox(opt, key=f"mc_cb_{q['id']}_{opt_idx}"):
                            selected_opts.append(opt)
                            
                    st.session_state[f"mc_ans_{q['id']}"] = ", ".join(selected_opts) if selected_opts else "未作答"
                
                st.markdown("---")
                st.markdown("<div class='mc-question'>🔥 Final Open Question:</div>", unsafe_allow_html=True)
                st.session_state.open_question_ans = st.text_area("覺得我哋嘅概念最特別是什麼？ (What makes our concept truly special?)", st.session_state.open_question_ans)

            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Gallery (Require 4+ Photos)")
            files = st.file_uploader("Upload up to 8 Photos (最少 4 張)", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                h_idx = min(st.session_state.hero_index, len(files)-1) if files else 0
                hero_choice = st.radio("🌟 必須選取 Highlight Hero Banner", [f"P{i+1}" for i in range(len(files))], index=h_idx, horizontal=True)
                st.session_state.hero_index = int(hero_choice[1:]) - 1
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        if i in st.session_state.processed_photos: st.markdown('<div class="ai-status-tag">✨ AI READY</div>', unsafe_allow_html=True)
                        if st.button(f"🪄 AI P{i+1}", key=f"ai_{i}"):
                            st.session_state.processed_photos[i] = manna_ai_enhance(f)
                            st.rerun()
                        img_disp = st.session_state.processed_photos.get(i, ImageOps.exif_transpose(Image.open(f)))
                        border = "hero-border" if i == st.session_state.hero_index else ""
                        st.markdown(f'<div class="{border}">', unsafe_allow_html=True)
                        st.image(img_disp, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.header("📋 6 Platforms Generation & DB Sync")
        
        has_logo = bool(st.session_state.logo_white or st.session_state.logo_black)
        has_enough_photos = len(st.session_state.project_photos) >= 4
        has_completed_mc = len(st.session_state.mc_questions) == 20
        has_open_question = bool(st.session_state.open_question_ans.strip())
        
        st.markdown("<p style='color: #666; font-size: 12px;'>⚠️ 必須完成 20 題 MC、Open Question、上傳至少一個 Logo (黑或白) 及 至少 4 張相片，才可執行生成。</p>", unsafe_allow_html=True)
        
        if st.button("🪄 根據 20MC 答案一鍵生成 6 大平台文案"):
            if not has_logo:
                st.markdown("<div class='blocker-alert'>🚨 <b>阻截警告：</b> 請先回到 'Data Collector' 上傳 Client Logo (黑白皆可)。</div>", unsafe_allow_html=True)
            elif not has_enough_photos:
                st.markdown(f"<div class='blocker-alert'>🚨 <b>阻截警告：</b> 請先上傳至少 4 張活動相片 (目前 {len(st.session_state.project_photos)} 張)。</div>", unsafe_allow_html=True)
            elif not has_completed_mc or not has_open_question:
                st.markdown("<div class='blocker-alert'>🚨 <b>阻截警告：</b> 請先生成並完成 20 條專案靈魂測驗題及 Open Question。</div>", unsafe_allow_html=True)
            else:
                collected_answers = []
                for q in st.session_state.mc_questions:
                    ans = st.session_state.get(f"mc_ans_{q['id']}", "未作答")
                    collected_answers.append(f"Q: {q['question']} | A: {ans}")
                answers_str = "\n".join(collected_answers)

                # 重大更新：嚴格控制 Instagram 輸出的語言與字數限制
                generation_prompt = f"""
                As an AI PR Strategist, analyze the following project data and user MC answers to extract the 'Challenge' and 'Solution', then generate content for 6 platforms based on Firebean's PDF Style Guides.
                
                Project: {st.session_state.project_name}
                Category: {st.session_state.who_we_help} | What We Do: {st.session_state.what_we_do} | Scope: {st.session_state.scope_of_word}
                YouTube Link: {st.session_state.youtube_link}
                
                === 20 MC Answers Analysis ===
                {answers_str}
                
                === The "Special Concept" (Open Question) ===
                {st.session_state.open_question_ans}
                
                OUTPUT REQUIREMENT:
                You MUST output ONLY a JSON object containing the exact structure below. Adhere strictly to word counts!
                1. First, summarize 'challenge' and 'solution' (under 100 words each) based on the MC answers.
                2. Then generate the 6 platform contents applying the PDF rules.

                {{
                    "challenge_summary": "Extracted boring challenge (<100 words)",
                    "solution_summary": "Extracted creative translation (<100 words)",
                    "1_google_slide": {{
                        "language": "English ONLY",
                        "hook": "Professional business hook based on the Open Question concept.",
                        "shift": "Introduce Firebean's Interactive-Trust Framework.",
                        "proof": "3 bullet points showing logic/results."
                    }},
                    "2_facebook_post": {{
                        "language": "Traditional Chinese",
                        "style": "The Grounded Expert / Weekend Planner. Target: Parents/Professionals. Funnel structure (Pain point -> Solution -> Action). Use emojis. Include clear CTA to watch YouTube."
                    }},
                    "3_threads_post": {{
                        "language": "Canto-English Code-Switching",
                        "style": "The Creative Insider. 'Contrast Flex'. Question hook. Short sentences (<50 chars), slang (世一, Firm, Vibe). Text-first approach."
                    }},
                    "4_instagram_post": {{
                        "language": "主要為繁體中文 (夾雜少量英文潮語如 Vibe, Chill)",
                        "style": "The Lifestyle Curator. Aesthetic First. 視覺旁白。第一句必須 Catchy。⚠️ 嚴格限制：總字數絕對不能超過 150 字！極度精簡，排版要靚，多用 Emoji 分隔。"
                    }},
                    "5_linkedin_post": {{
                        "language": "English ONLY",
                        "style": "Institutional Cool. Thought Leadership. Interpretative writing. Bridge Structure (Challenge -> Insight -> Proof). 150-300 words."
                    }},
                    "6_website": {{
                        "en": {{"title": "Punchy EN Title", "content": "Professional EN description (max 100 words)."}},
                        "tc": {{"title": "Punchy TC Title", "content": "Professional TC description (max 100 words)."}},
                        "jp": {{"title": "Punchy JP Title", "content": "Professional JP description (max 100 words)."}}
                    }}
                }}
                """
                with st.spinner("🧠 正在根據 20 題答案及 PDF 指引，萃取並生成六大平台多語系文案..."):
                    res_json = call_gemini_sdk(generation_prompt, is_json=True)
                    if res_json:
                        try:
                            st.session_state.ai_content = json.loads(res_json)
                            st.session_state.challenge = st.session_state.ai_content.get("challenge_summary", "")
                            st.session_state.solution = st.session_state.ai_content.get("solution_summary", "")
                            st.success("✅ 六大平台文案已完美生成！完全符合 Firebean DNA。")
                        except: 
                            log_debug("JSON Parsing Error.", "error")
                            st.error("生成格式出錯，請查看 Debug Terminal")
                            
        if st.session_state.ai_content: 
            st.json(st.session_state.ai_content)
            
        if st.button("🚀 Confirm & Sync to Master Ecosystem"):
            if not st.session_state.ai_content:
                st.error("請先生成文案再進行同步！")
            else:
                with st.spinner("🔄 正在雙軌發送數據至 Master DB (Google Sheet) 及自動生成 Google Slide..."):
                    try:
                        b64_imgs = []
                        for i, f in enumerate(st.session_state.project_photos):
                            img = st.session_state.processed_photos.get(i, ImageOps.exif_transpose(Image.open(f)))
                            buf = io.BytesIO()
                            img.convert("RGB").save(buf, format="JPEG", quality=80)
                            b64_imgs.append(base64.b64encode(buf.getvalue()).decode())

                        has_black = bool(st.session_state.logo_black)
                        has_white = bool(st.session_state.logo_white)
                        log_debug(f"Packaging Payload: {len(b64_imgs)} photos. Black Logo: {has_black}. White Logo: {has_white}", "info")

                        payload = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "event_date": f"{st.session_state.event_year} {st.session_state.event_month}",
                            "venue": st.session_state.venue,
                            "youtube_link": st.session_state.youtube_link,
                            "category_who": ", ".join(st.session_state.who_we_help),
                            "category_what": ", ".join(st.session_state.what_we_do),
                            "scope_of_work": ", ".join(st.session_state.scope_of_word),
                            "challenge": st.session_state.challenge,
                            "solution": st.session_state.solution,
                            "open_question": st.session_state.open_question_ans,
                            "ai_content": st.session_state.ai_content,
                            "logo_white": st.session_state.logo_white,
                            "logo_black": st.session_state.logo_black,
                            "images": b64_imgs
                        }

                        sheet_ok = False
                        slide_ok = False
                        
                        try:
                            log_debug("Sending to Google Sheet Apps Script...", "info")
                            res_sheet = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                            sheet_ok = res_sheet.status_code in [200, 302]
                            log_debug(f"Sheet Response: {res_sheet.status_code}", "success" if sheet_ok else "warning")
                        except Exception as e:
                            log_debug(f"Sheet Sync Error: {str(e)}", "error")

                        try:
                            log_debug("Sending to Google Slide Apps Script...", "info")
                            res_slide = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                            slide_ok = res_slide.status_code in [200, 302]
                            log_debug(f"Slide Response: {res_slide.status_code}", "success" if slide_ok else "warning")
                        except Exception as e:
                            log_debug(f"Slide Sync Error: {str(e)}", "error")

                        if sheet_ok and slide_ok:
                            st.balloons()
                            st.success("✅ 真實數據已成功同步至 Master DB，並成功觸發 Google Slide 自動生成！")
                        elif sheet_ok and not slide_ok:
                            st.warning("⚠️ 數據已成功寫入 Google Sheet，但 Google Slide 生成失敗（請檢查 Slide Apps Script）。")
                        elif not sheet_ok and slide_ok:
                            st.warning("⚠️ Google Slide 已成功生成，但 Google Sheet 寫入失敗（請檢查 Sheet Apps Script）。")
                        else:
                            st.error("❌ Google Sheet 與 Google Slide 同步皆失敗，請查看最底部的 Debug Terminal。")
                            
                    except Exception as e:
                        st.error(f"❌ 打包數據時發生錯誤: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 5. 永久除錯終端 ---
    st.markdown("---")
    with st.expander("🛠️ Firebean Brain Debug Terminal (Permanent)", expanded=False):
        col_t, _ = st.columns([1, 4])
        with col_t:
            if st.button("🔍 Test API Connection"): test_api_connection()
        if not st.session_state.debug_logs:
            st.write("Ready for Institutional Cool Debugging.")
        else:
            for l in reversed(st.session_state.debug_logs):
                cls = f"debug-{l['type']}"
                st.markdown(f"<div class='debug-terminal {cls}'>[{l['time']}] {l['msg']}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
