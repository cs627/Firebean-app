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

**CRITICAL INSTRUCTION FOR '6_website' (Magazine Feature Article)**: 
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

**CRITICAL INSTRUCTIONS FOR SOCIAL MEDIA POSTS (2_facebook, 3_threads, 4_instagram, 5_linkedin)**:
You must strictly follow these platform-specific guidelines to create synergistic PR content. 

1. '2_facebook_post' (廣泛觸及與資訊大本營):
   - Word Count: 100 - 250 words.
   - Tone: 親切有溫度、故事化互動。語氣要像對話，多使用「你」作為溝通對象。
   - Content: 從情感出發，分享長篇幅的故事或過往活動的精彩回顧，點出痛點與解決方案。
   - Format: 必須包含明確的報名資訊（時間、地點、票務詳情）及 CTA 連結。
   - Language: 香港繁體中文 (可適度夾雜廣東話口語)。

2. '4_instagram_post' (視覺衝擊與真實幕後花絮):
   - Word Count: STRICTLY < 150 words. 最關鍵是頭兩行（首 125 個字元），必須在「展開」前抓住眼球。
   - Tone: 極簡視覺化、真實「貼地」。
   - Content: 圈內人視角 (Behind-the-scenes)。聚焦公關團隊籌備項目的真實片段、場地佈置過程。
   - Format: 配合大量 Emoji 分段，並「必帶專業 Hashtags」營造高端視覺感。
   - Language: 香港繁體中文。

3. '3_threads_post' (實時客廳與觀點碰撞):
   - Word Count: 短小精悍，< 50 words (Max 200 characters).
   - Tone: 幽默口語化、隨性但具批判性。具備網絡 Meme 潛力。
   - Content: 提問與反傳統開局。放棄「活動即將舉行」這類廣播，改用提問式或拋出反傳統觀點 (例如："大家參加這類活動最怕遇到咩伏？我哋今次特登改咗呢樣嘢👇")。旨在引發社群共鳴與快節奏討論。
   - Language: 最地道的廣東話/網絡用語，語氣要 casual。

4. '5_linkedin_post' (B2B 價值與思想領導力):
   - Word Count: 150 - 300 words. 段落必須分明。
   - Tone: 權威 B2B、專業顧問風格。強調數據、ROI 與行業領導地位。
   - Content: 思想領導力 (Thought Leadership)。由創辦人或高層分享舉辦項目的初衷、克服的商業挑戰，解釋「為何這項目對行業發展至關重要」及「大眾的誤解」。突顯活動的 Networking 價值。
   - Language: 雙語並行 (English first, followed by Traditional Chinese)。

DO NOT output any conversational text outside the JSON object.
"""

# --- 2. 核心邏輯與安全性防禦 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key:
        log_debug("🚨 找不到 API Key", "error")
        st.error("🚨 找不到 API Key")
        return None
    try:
        genai.configure(api_key=secret_key)
        model = genai.GenerativeModel(model_name=STABLE_MODEL_ID, system_instruction=FIREBEAN_SYSTEM_PROMPT)
        contents = [prompt]
        
        log_debug(f"🤖 發送 AI 任務中... [目標格式: {'JSON' if is_json else 'Text'}]", "info")
        
        if image_files:
            for f in image_files:
                if hasattr(f, "seek"): f.seek(0) # 確保這裡也是從頭讀起
                img = Image.open(f)
                img.thumbnail((800, 800))
                contents.append(img)
            log_debug(f"📸 已附加 {len(image_files)} 張相片給 AI 進行視覺掃描", "info")
        
        start_time = time.time()
        
        response = model.generate_content(contents, generation_config={
            "response_mime_type": "application/json" if is_json else "text/plain",
            "temperature": 0.2
        })
        
        calc_time = round(time.time() - start_time, 2)
        
        if response and response.text:
            text = response.text.strip()
            log_debug(f"✅ AI 運算完成 (耗時 {calc_time} 秒)！原始輸出截取: {text[:80]}...", "success")
            
            if not is_json: return text
            
            match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
            json_str = match.group(0) if match else text
            
            try:
                # 🌟 修復核心：單純驗證 JSON，不強制解構
                data = json.loads(json_str)
                return json_str
            except:
                log_debug("⚠️ AI 輸出的 JSON 格式有雜訊，系統嘗試自動修復中...", "warning")
                return json_str
    except Exception as e:
        log_debug(f"❌ AI 運算發生錯誤: {str(e)[:100]}", "error")
        st.error("❌ AI 運算發生錯誤，請查看 Debug Terminal 日誌。")
    return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector",
        "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": "2026", "event_month": "FEB",
        "category": WHO_WE_HELP_OPTIONS[0], "what_we_do": [], "scope": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", 
        "challenge": "", "solution": "", "visual_facts": "",
        "has_auto_jumped": False 
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
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = "2026 旗艦同步測試"
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.youtube = "https://youtube.com/firebean_sync_demo"
    st.session_state.category = "LIFESTYLE & CONSUMER"
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope = ["Theme Design", "Event Production", "Concept Development"]
    st.session_state.open_question_ans = "將 20 個通用診斷問題轉化為一套連貫、引人入勝且可操作的跨平台策略。"
    
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    
    st.session_state.mc_questions = [{"id": i+1, "question": f"診斷指標 {i+1}？", "options": ["戰略優化", "維持"]} for i in range(20)]
    for i in range(1, 21): st.session_state[f"ans_{i}"] = ["戰略優化"]
    
    dummy_logo = base64.b64encode(create_dummy_image("#000000", "LOGO").getvalue()).decode()
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
        .debug-terminal { background: #1E1E1E !important; color: #00FF00 !important; padding: 15px; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px; height: 300px; overflow-y: scroll; }
        
        .stButton > button {
            min-height: 55px !important;
            font-size: 18px !important;
            font-weight: 700 !important;
        }

        /* 🚀 核心更新：將左上角的按鈕偽裝成 Firebean Logo */
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div[data-testid="stElementContainer"] button,
        div.element-container:has(#logo-anchor) + div.element-container button {
            background-image: url('https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: left center;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            min-height: 180px !important; 
            width: 540px !important;      
            padding: 0 !important;
            margin-top: -10px;
        }
        div.element-container:has(#logo-anchor) + div.element-container button:hover,
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div[data-testid="stElementContainer"] button:hover {
            transform: scale(1.03);
            background-color: transparent !important;
        }
        div.element-container:has(#logo-anchor) + div.element-container button p,
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div[data-testid="stElementContainer"] button p {
            display: none !important;
        }
    </style>""", unsafe_allow_html=True)

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

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

    c1, c2 = st.columns([1, 1])
    with c1: 
        st.markdown('<span id="logo-anchor"></span>', unsafe_allow_html=True)
        if st.button("HOME", key="logo_btn", help="點擊返回 Project Collector 主頁"):
            st.session_state.active_tab = "Project Collector"
            st.rerun()
    with c2: 
        st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    if percent == 100 and st.session_state.active_tab == "Project Collector" and not st.session_state.get("has_auto_jumped", False):
        st.session_state.has_auto_jumped = True  
        st.toast("🎯 100% 完成！正在自動跳轉...")
        time.sleep(1.2)
        st.session_state.active_tab = "Review & Multi-Sync"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    nav_cols = st.columns(3)
    
    if nav_cols[0].button("Project Collector", use_container_width=True, type="primary" if st.session_state.active_tab == "Project Collector" else "secondary"):
        st.session_state.active_tab = "Project Collector"
        st.rerun()
        
    if nav_cols[1].button("Review & Multi-Sync", use_container_width=True, type="primary" if st.session_state.active_tab == "Review & Multi-Sync" else "secondary"):
        st.session_state.active_tab = "Review & Multi-Sync"
        st.rerun()
        
    if nav_cols[2].button("老細一鍵填充 (深度內容測試)", use_container_width=True):
        fill_dummy_data()
        st.rerun()

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

    # --- TAB 分頁內容 ---
    if st.session_state.active_tab == "Project Collector":
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
            if st.button("生成 20 題繁中診斷題目"):
                if not st.session_state.project_photos: 
                    st.error("請先上傳相片。")
                else:
                    # 🚀 修正 1：加入狀態追蹤，增加載入體驗並修正縮排
                    with st.status("🧠 AI 大腦啟動中...", expanded=True) as status:
                        st.write("📸 正在提取並分析活動相片的視覺細節...")
                        vision_prompt = """
                        請使用繁體中文 (Traditional Chinese)，詳細掃描並提取這些活動相片中的實體事實 (Facts)。
                        請務必精準識別並描述以下五大細節，作為後續 PR 診斷之客觀依據：
                        1. Branding (品牌識別與曝光程度)
                        2. 現場佈置 (Decor & 氛圍)
                        3. 科技設備 (Tech & 互動裝置)
                        4. 人流規模 (Crowd & 參與度)
                        5. 餐飲細節 (F&B 服務水準)
                        """
                        facts = call_gemini_sdk(vision_prompt, image_files=st.session_state.project_photos)
                        
                        st.write("📊 視覺分析完成！正在消化 SOW 與客戶背景資料...")
                        time.sleep(1)
                        
                        st.write("📝 開始構思 20 條專業 PR 診斷題目...")
                        mc_prompt = f"""
請基於以下專案背景資料與相片分析事實，生成 20 題繁體中文的專業 PR 診斷選擇題 (MC)，以評估此專案的潛在挑戰與優化空間。
【專案背景資料】
- 客戶與專案名稱：{st.session_state.client_name} / {st.session_state.project_name}
- 產業類別 (Category)：{st.session_state.category}
- 活動時間與地點：{st.session_state.event_year} {st.session_state.event_month} 於 {st.session_state.venue}
- 核心服務形式 (What we do)：{", ".join(st.session_state.what_we_do)}
- 工作範圍 (Scope of Work)：{", ".join(st.session_state.scope)}

【現場/視覺相片分析事實】
{facts}

請確保題目具備深度，能引導出具體的痛點。
必須嚴格輸出為 JSON 陣列格式：[{{\"id\":1,\"question\":\"問題內容...\",\"options\":[\"選項A\",\"選項B\"]}}]
"""
                        res = call_gemini_sdk(mc_prompt, is_json=True)
                        if res: 
                            st.session_state.mc_questions = json.loads(res)
                            status.update(label="✅ 分析與題目生成完畢！", state="complete", expanded=False)
                            time.sleep(1)
                            st.rerun()

            if st.session_state.mc_questions:
                if isinstance(st.session_state.mc_questions, list):
                    for q in st.session_state.mc_questions:
                        if isinstance(q, dict) and 'id' in q:
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
                        try: 
                            if hasattr(f, "seek"): f.seek(0)
                            st.image(Image.open(f), use_container_width=True)
                        except: 
                            st.image(f, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("生成六大平台對接文案"):
            with st.spinner("AI Strategist 正在構思文案..."):
                mc_sum = [f"Q:{q['question']} A:{st.session_state.get(f'ans_{q['id']}')}" for q in st.session_state.mc_questions if isinstance(q, dict)]
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
                    if isinstance(data, list) and len(data) > 0:
                        data = data[0]
                    if isinstance(data, dict):
                        st.session_state.ai_content = data
                        st.session_state.challenge = data.get("challenge_summary", "尚未生成")
                        st.session_state.solution = data.get("solution_summary", "尚未生成")
                        st.toast("✅ 策略與文案已成功生成！")
                        time.sleep(1)
                        st.rerun() 

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("Confirm & Sync (Sheet + Slide + Drive)", type="primary", use_container_width=True):
                with st.spinner("🔄 同步中..."):
                    try:
                        # 🚀 修正 2：指標重置與圖片格式壓縮標準化，解決 Drive 0 Byte 及 Slide 讀不到圖片的問題
                        imgs = []
                        for f in st.session_state.project_photos:
                            if hasattr(f, "seek"): 
                                f.seek(0) # 關鍵：將檔案讀取點重設回開頭
                            
                            try:
                                # 將圖片轉換為統一的 RGB/JPEG 格式，並限制大小在 1600px 內，防止檔案過大
                                img = Image.open(f).convert("RGB")
                                img.thumbnail((1600, 1600))
                                buf = io.BytesIO()
                                img.save(buf, format="JPEG", quality=85)
                                imgs.append(base64.b64encode(buf.getvalue()).decode())
                            except Exception as e:
                                log_debug(f"圖片轉換錯誤: {e}", "error")
                                # 如果有例外狀況，就退回原本的讀取方式
                                if hasattr(f, "seek"): f.seek(0)
                                imgs.append(base64.b64encode(f.read() if hasattr(f, "read") else f.getvalue()).decode())

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
                            "logo_white": st.session_state.logo_white, # Logo 上傳時已經是 base64 string
                            "logo_black": st.session_state.logo_black,
                            "images": imgs,
                            "ai_content": st.session_state.ai_content
                        }
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sync: Sheet {r1.status_code}, Slide {r2.status_code}", "success")
                        st.balloons(); st.success("✅ 全部數據同步對位成功！")
                    except Exception as e: 
                        log_debug(f"Sync Fail: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🛠️ Debug Terminal & System Logs", expanded=False):
        st.markdown("### 🔑 API Key 連線測試 (讀取 Streamlit Secrets)")
        
        if st.button("執行連線測試", use_container_width=True):
            with st.spinner("正在讀取系統 Secrets 並連線中..."):
                secret_key = st.secrets.get("GEMINI_API_KEY", "")
                if not secret_key:
                    st.error("❌ 找不到 API Key！請檢查 Streamlit Cloud 的 Advanced Settings > Secrets 裡面是否有設定 `GEMINI_API_KEY`。")
                    log_debug("API Key 測試失敗：找不到 Secret。", "error")
                else:
                    try:
                        genai.configure(api_key=secret_key)
                        model = genai.GenerativeModel(STABLE_MODEL_ID)
                        res = model.generate_content("Reply only the word: SUCCESS")
                        if res and "SUCCESS" in res.text.upper():
                            st.success("✅ API Key 測試成功！Streamlit Secrets 運作正常。")
                            log_debug("系統 API Key (Secrets) 連線測試成功。", "success")
                        else:
                            st.error("❌ 連線異常，請確認 API Key 的權限或額度。")
                    except Exception as e:
                        st.error(f"❌ 錯誤: {e}")
                        log_debug(f"系統 API Key 測試失敗: {e}", "error")

        st.markdown("### 📝 System Logs")
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__": main()
