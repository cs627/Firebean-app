import streamlit as st
import google.generativeai as genai
import requests
from PIL import Image
import io
import json
import base64

# --- FIREBEAN BRAIN GUIDELINES (SYSTEM PROMPT) ---
FIREBEAN_BRAIN_GUIDELINES = """
You are "Firebean Brain", the core AI of Firebean, a top Hong Kong PR agency.
Your Identity: "The Architect of Public Engagement".
Your Tone: "Institutional Cool" - blending "Institutional Authority" (Government/Trust) with "Lifestyle Creativity" (Fun/Engagement).

CORE PHILOSOPHY:
1. "Create to Engage": We design engagement ecosystems, not just events.
2. "Turn Policy into Play": We make dry government policies (e.g., Building Laws, Basic Law) fun and accessible via gamification.
3. "The Interactive-Trust Framework": Every project must have "Strategic Distillation" (Story) and "Creative Gamification" (Play).

COMPETITIVE DIFFERENTIATION:
- "The Slash Capability": Rigor of a government consultant + Soul of a creative boutique.
- "Government-Grade Execution": 100% Tender-Ready compliance (BD, CMAB experience).
- No "Roll-up Banners": We do "Roving Exhibitions" as "Professional Playgrounds" (3D Art-tech, Flight Simulators, Pokemon-style games).
- "Hard Knowledge, Soft Landing": Parent-child workshops to increase dwell time.

PLATFORM WRITING RULES (STRICTLY FOLLOW):

1. WEBSITE (SEO/GEO):
   - First 200 Words Rule: Answer user pain points immediately.
   - Style: Professional English or Traditional Chinese. Use bold data and bullet points.

2. LINKEDIN (Business Leader View):
   - Structure: "Bridge Structure" -> Boring Challenge -> Creative Translation -> Data Result.
   - Style: Grounded Expert. No fluff. Confident.

3. FACEBOOK (Practical Parent / Weekend Planner):
   - Focus: "Weekend Good Place" (週末好去處), "Edutainment" (寓教於樂).
   - Style: HK Traditional Chinese (Written + Spoken). Friendly, like a planner friend. Use Emojis.

4. INSTAGRAM (Lifestyle Curator):
   - Aesthetic First: Focus on "Instagrammability", "3D Art-tech", "Immersive".
   - Style: Trendy Canto-English (Code-mixing). "Vibe is Chill", "Full of surprises".
   - Soft Sell: Experience first, policy second.

5. THREADS (The Unfiltered Creator / Industry Insider):
   - Contrast Flex: "Who knew the Buildings Dept could be this cool?".
   - Style: Raw & Real. Canto-English. Short, punchy sentences. "Firm", "Slay", "World Class" (世一).
   - Content: Behind-the-scenes struggles, self-deprecation, "Insider Info".

TASK:
Generate content based on the provided project details.
Return the output as a valid JSON object with the exact keys requested.
"""

# --- TRANSLATIONS ---
TRANSLATIONS = {
    "Chinese (繁體中文)": {
        "page_title": "Firebean AI 指揮中心",
        "sidebar_title": "🔥 Firebean AI",
        "config_title": "🔐 設定",
        "api_key_label": "Gemini API 金鑰",
        "api_key_success": "API 金鑰已設定",
        "api_key_warning": "請輸入 Gemini API 金鑰",
        "assets_title": "📂 專案素材",
        "client_logo_label": "客戶 Logo URL",
        "drive_folder_label": "專案 Drive 資料夾",
        "youtube_embed_label": "YouTube 嵌入代碼",
        "best_image_label": "精選圖片 URL",
        "tab1_title": "💬 員工聊天機器人 (訪談)",
        "tab2_title": "⚙️ 管理儀表板 (審核)",
        "tab3_title": "🗂️ 投影片預覽",
        "chatbot_header": "💬 Firebean 員工聊天機器人",
        "progress_title": "📊 收集進度",
        "chatbot_sub": "🤖 Firebean Brain 助手",
        "chat_placeholder": "告訴我關於活動的資訊... (例如：'客戶是 CMAB，日期是 2024-05-10')",
        "manual_entry_title": "🛠️ 手動資料輸入 & 圖片上傳",
        "date_label": "活動日期 (YYYY-MM-DD)",
        "client_label": "客戶名稱",
        "project_label": "專案名稱",
        "venue_label": "地點",
        "youtube_link_label": "YouTube 連結",
        "transcript_label": "原始逐字稿 / 專案筆記 (詳細)",
        "image_upload_header": "📸 圖片上傳",
        "image_upload_label": "上傳活動照片",
        "generate_btn": "🚀 啟動 Firebean Brain (生成所有素材)",
        "admin_header": "⚙️ 管理儀表板 (審核 & 發布)",
        "cat_title": "🏷️ 分類",
        "cat_who_label": "分類 (對象)",
        "cat_what_label": "分類 (內容)",
        "highlight_order_label": "精選順序",
        "pr_copy_title": "📝 多語言公關文案",
        "social_title": "📱 社群媒體內容",
        "approve_btn": "✅ 批准並儲存至資料庫",
        "save_success": "✅ 成功儲存至資料庫！",
        "save_error": "❌ 儲存失敗。狀態碼：",
        "conn_error": "❌ 連線錯誤：",
        "initial_msg": "你好！我是 Firebean Brain (Beta)。我來協助你撰寫完美的案例研究。請在側邊欄或表單中填寫專案詳情，並分享原始逐字稿。我準備好將政策轉化為遊戲了！",
        "progress_labels": {
            "Date": "日期",
            "Client": "客戶",
            "Project": "專案",
            "Venue": "地點",
            "Notes": "筆記",
            "Photos": "照片"
        },
        "lang_label": "語言 / Language",
        "bot_extracted": "收到！已更新以下欄位：{fields}。還有什麼關於結果或「氛圍」的資訊嗎？",
        "bot_fallback": "已將其加入專案筆記。請繼續分享活動詳情或結果！",
        "bot_more_info": "已將其加入專案筆記。請告訴我更多！",
        "bot_no_api": "已將其加入專案筆記。（注意：設定 API 金鑰以啟用自動提取）",
        "gen_success": "✅ 內容生成成功！請在管理儀表板分頁中查看。",
        "gen_error": "生成失敗：",
        "provide_transcript": "請提供原始逐字稿。"
    },
    "English": {
        "page_title": "Firebean AI Command Center",
        "sidebar_title": "🔥 Firebean AI",
        "config_title": "🔐 Configuration",
        "api_key_label": "Gemini API Key",
        "api_key_success": "API Key Configured",
        "api_key_warning": "Please enter Gemini API Key",
        "assets_title": "📂 Project Assets",
        "client_logo_label": "Client Logo URL",
        "drive_folder_label": "Project Drive Folder",
        "youtube_embed_label": "YouTube Embed Code",
        "best_image_label": "Best Image URL",
        "tab1_title": "💬 Staff Chatbot (Interviewer)",
        "tab2_title": "⚙️ Admin Dashboard (Review)",
        "tab3_title": "🗂️ Slide Preview",
        "chatbot_header": "💬 Firebean Staff Chatbot",
        "progress_title": "📊 Collection Progress",
        "chatbot_sub": "🤖 Firebean Brain Assistant",
        "chat_placeholder": "Tell me about the event... (e.g., 'Client is CMAB, Date was 2024-05-10')",
        "manual_entry_title": "🛠️ Manual Data Entry & Image Upload",
        "date_label": "Event Date (YYYY-MM-DD)",
        "client_label": "Client Name",
        "project_label": "Project Name",
        "venue_label": "Venue",
        "youtube_link_label": "YouTube Link",
        "transcript_label": "Raw Transcript / Project Notes (Detailed)",
        "image_upload_header": "📸 Image Upload",
        "image_upload_label": "Upload Event Photos",
        "generate_btn": "🚀 Activate Firebean Brain (Generate All Assets)",
        "admin_header": "⚙️ Admin Dashboard (Review & Publish)",
        "cat_title": "🏷️ Categorization",
        "cat_who_label": "Category Who",
        "cat_what_label": "Category What",
        "highlight_order_label": "Highlight Order",
        "pr_copy_title": "📝 Multilingual PR Copy",
        "social_title": "📱 Social Media Content",
        "approve_btn": "✅ Approve & Save to Database",
        "save_success": "✅ Successfully saved to database!",
        "save_error": "❌ Failed to save. Status Code:",
        "conn_error": "❌ Connection Error:",
        "initial_msg": "Hello! I am the Firebean Brain (Beta). I'm here to help you craft the perfect case study. Please fill in the Project Details in the sidebar or form, and share the Raw Transcript. I'm ready to turn Policy into Play!",
        "progress_labels": {
            "Date": "Date",
            "Client": "Client",
            "Project": "Project",
            "Venue": "Venue",
            "Notes": "Notes",
            "Photos": "Photos"
        },
        "lang_label": "Language / 語言",
        "bot_extracted": "Got it! I've updated the following fields: {fields}. What else can you tell me about the results or the 'vibe'?",
        "bot_fallback": "I've added that to the project notes. Please continue sharing the event details or results!",
        "bot_more_info": "I've added that to the project notes. Tell me more!",
        "bot_no_api": "I've added that to the project notes. (Note: Configure API Key for auto-extraction)",
        "gen_success": "✅ Content Generated Successfully! Please review in the Admin Dashboard tab.",
        "gen_error": "Generation Failed: ",
        "provide_transcript": "Please provide a Raw Transcript."
    }
}

# --- INITIALIZATION ---
def init_session_state():
    # List of all 35 database fields required
    fields = [
        "event_date", "client_name", "project_name", "venue",
        "category_who", "category_what", "highlight_order",
        "raw_transcript", "youtube_link", "gallery_image_urls",
        "project_drive_folder", "best_image_url", "client_logo_url", "youtube_embed_code",
        "title_en", "challenge_en", "solution_en", "result_en",
        "title_ch", "challenge_ch", "solution_ch", "result_ch",
        "title_jp", "challenge_jp", "solution_jp", "result_jp",
        "linkedin_draft", "fb_post",
        "ig_caption", "threads_post", "newsletter_topic",
        "slide_1_cover", "slide_2_challenge", "slide_3_solution", "slide_4_results"
    ]
    for field in fields:
        default_val = [] if "slide_" in field else ""
        st.session_state.setdefault(field, default_val)
    
    # Chat history for the "Interviewer"
    if "messages" not in st.session_state:
        # Default to Chinese initial message if not set, or generic
        st.session_state.messages = [
            {"role": "assistant", "content": TRANSLATIONS["Chinese (繁體中文)"]["initial_msg"]}
        ]

# --- UI STYLING: NEUMORPHISM ---
def apply_neumorphism_style():
    st.markdown("""
        <style>
        /* Main background */
        .stApp {
            background-color: #e0e5ec;
        }
        
        /* Neumorphic Container */
        .neu-container {
            background-color: #e0e5ec;
            border-radius: 20px;
            box-shadow: 9px 9px 16px rgb(163,177,198,0.6), -9px -9px 16px rgba(255,255,255, 0.5);
            padding: 25px;
            margin-bottom: 20px;
        }
        
        /* Neumorphic Input */
        div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] {
            background-color: #e0e5ec !important;
            border-radius: 10px !important;
            box-shadow: inset 5px 5px 10px #b8bec5, inset -5px -5px 10px #ffffff !important;
            border: none !important;
        }
        
        /* Buttons */
        .stButton>button {
            background-color: #e0e5ec !important;
            color: #444 !important;
            border-radius: 12px !important;
            border: none !important;
            box-shadow: 6px 6px 12px #b8bec5, -6px -6px 12px #ffffff !important;
            transition: all 0.2s ease !important;
            font-weight: 600 !important;
        }
        .stButton>button:hover {
            box-shadow: 2px 2px 5px #b8bec5, -2px -2px 5px #ffffff !important;
            transform: translateY(2px);
        }
        .stButton>button:active {
            box-shadow: inset 4px 4px 8px #b8bec5, inset -4px -4px 8px #ffffff !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #e0e5ec;
            box-shadow: 4px 0px 10px rgba(0,0,0,0.05);
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background-color: transparent !important;
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #e0e5ec !important;
            border-radius: 10px 10px 0 0 !important;
            box-shadow: 4px 4px 8px #b8bec5, -4px -4px 8px #ffffff !important;
            padding: 10px 20px !important;
            border: none !important;
        }
        
        /* Logo styling */
        .logo-container {
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
        }
        .logo-img {
            width: 180px;
            filter: drop-shadow(4px 4px 6px rgba(0,0,0,0.1));
        }
        /* Typography */
        h1, h2, h3, p, label {
            color: #4a4a4a !important;
            font-family: 'Inter', sans-serif;
        }
        
        /* Expander styling */
        .stExpander {
            background-color: #e0e5ec !important;
            border-radius: 15px !important;
            box-shadow: 6px 6px 12px #b8bec5, -6px -6px 12px #ffffff !important;
            border: none !important;
            margin-bottom: 20px !important;
        }
        
        /* Chat messages */
        .stChatMessage {
            background-color: #e0e5ec !important;
            border-radius: 15px !important;
            box-shadow: 4px 4px 8px #b8bec5, -4px -4px 8px #ffffff !important;
            margin-bottom: 10px !important;
            border: none !important;
        }
        
        /* Success/Error messages */
        .stAlert {
            border-radius: 12px !important;
            box-shadow: 4px 4px 8px #b8bec5, -4px -4px 8px #ffffff !important;
            border: none !important;
        }
        /* Mobile Responsiveness */
        @media (max-width: 768px) {
            .logo-img {
                width: 120px;
            }
            .neu-container {
                padding: 15px;
                border-radius: 15px;
            }
            h1 {
                font-size: 1.5rem !important;
            }
            .status-pill {
                padding: 6px 12px;
                font-size: 0.75rem;
                margin-right: 8px;
                margin-bottom: 8px;
            }
            /* Make tabs scrollable on small screens */
            .stTabs [data-baseweb="tab-list"] {
                overflow-x: auto;
                white-space: nowrap;
                padding-bottom: 10px;
            }
        }
        
        /* Progress Indicator */
        .status-pill {
            display: inline-block;
            padding: 8px 18px;
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-right: 12px;
            margin-bottom: 12px;
            background-color: #e0e5ec;
            box-shadow: 4px 4px 8px #b8bec5, -4px -4px 8px #ffffff;
            border: 1px solid rgba(255,255,255,0.2);
            transition: all 0.3s ease;
        }
        .status-complete {
            color: #2e7d32 !important;
            box-shadow: inset 2px 2px 5px #b8bec5, inset -2px -2px 5px #ffffff;
        }
        .status-pending {
            color: #757575 !important;
            opacity: 0.7;
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">', unsafe_allow_html=True)

def display_progress(lang):
    t = TRANSLATIONS[lang]
    required_fields = {
        t["progress_labels"]["Date"]: st.session_state["event_date"],
        t["progress_labels"]["Client"]: st.session_state["client_name"],
        t["progress_labels"]["Project"]: st.session_state["project_name"],
        t["progress_labels"]["Venue"]: st.session_state["venue"],
        t["progress_labels"]["Notes"]: st.session_state["raw_transcript"],
        t["progress_labels"]["Photos"]: st.session_state["gallery_image_urls"]
    }
    
    # Use a container for the pills
    pills_html = '<div style="display: flex; flex-wrap: wrap; margin-bottom: 20px;">'
    for label, value in required_fields.items():
        is_complete = bool(value and value.strip())
        status_class = "status-complete" if is_complete else "status-pending"
        icon = "✅" if is_complete else "⚪"
        pills_html += f'<div class="status-pill {status_class}">{icon} {label}</div>'
    pills_html += '</div>'
    st.markdown(pills_html, unsafe_allow_html=True)

# --- LOGO LOADING ---
@st.cache_data
def get_base64_logo(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode()
    except Exception:
        pass
    return None

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="Firebean AI", layout="wide", page_icon="🔥")
    init_session_state()
    # --- SIDEBAR: CONFIGURATION ---
    with st.sidebar:
        # Language Selector
        lang_options = ["Chinese (繁體中文)", "English"]
        lang = st.selectbox("語言 / Language", lang_options, index=0)
        t = TRANSLATIONS[lang]
        
        st.title(t["sidebar_title"])
        st.markdown(f"### {t['config_title']}")
        api_key = st.text_input(t["api_key_label"], type="password", value="AIzaSyAhhiB3djyljE0zkas8bMvvHXFOqNPYrVU")
        
        if api_key:
            genai.configure(api_key=api_key)
            st.success(t["api_key_success"])
        else:
            st.warning(t["api_key_warning"])

        st.markdown("---")
        st.markdown(f"### {t['assets_title']}")
        st.session_state["client_logo_url"] = st.text_input(t["client_logo_label"], value=st.session_state["client_logo_url"])
        st.session_state["project_drive_folder"] = st.text_input(t["drive_folder_label"], value=st.session_state["project_drive_folder"])
        st.session_state["youtube_embed_code"] = st.text_input(t["youtube_embed_label"], value=st.session_state["youtube_embed_code"])
        st.session_state["best_image_url"] = st.text_input(t["best_image_label"], value=st.session_state["best_image_url"])

    apply_neumorphism_style()

    # Logo Display (Using Base64 to avoid Google Drive blocking)
    logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
    logo_base64 = get_base64_logo(logo_url)
    
    if logo_base64:
        st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_base64}" class="logo-img"></div>', unsafe_allow_html=True)
    else:
        # Fallback to direct URL if base64 fails
        st.markdown(f'<div class="logo-container"><img src="{logo_url}" class="logo-img"></div>', unsafe_allow_html=True)

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs([t["tab1_title"], t["tab2_title"], t["tab3_title"]])

    # --- TAB 1: STAFF CHATBOT & COLLECTOR ---
    with tab1:
        st.header(t["chatbot_header"])
        
        # Progress Tracker
        st.markdown(f"### {t['progress_title']}")
        display_progress(lang)

        # Chat Interface for Interaction (The Main Lead)
        st.subheader(t["chatbot_sub"])
        
        # Display chat messages in a container
        chat_container = st.container()
        with chat_container:
            for message in st.session_state["messages"]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Chat Input (For refining transcript or asking questions)
        if prompt := st.chat_input(t["chat_placeholder"]):
            # Add user message to chat history
            st.session_state["messages"].append({"role": "user", "content": prompt})
            
            # AI Logic to "understand" and "extract" info from chat
            if api_key:
                try:
                    extractor_model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        system_instruction="Extract project details from the user message. Return JSON with keys: event_date, client_name, project_name, venue. If not found, leave empty string. Format date as YYYY-MM-DD.",
                        generation_config={"response_mime_type": "application/json"}
                    )
                    extraction_response = extractor_model.generate_content(prompt)
                    extracted_data = json.loads(extraction_response.text)
                    
                    # Auto-fill session state
                    updated = []
                    for k, v in extracted_data.items():
                        if v and not st.session_state[k]:
                            st.session_state[k] = v
                            updated.append(k.replace('_', ' ').title())
                    
                    if updated:
                        response = f"Got it! I've updated the following fields: {', '.join(updated)}. What else can you tell me about the results or the 'vibe'?"
                    else:
                        # Fallback logic for transcript
                        st.session_state["raw_transcript"] += f"\n\n[Chat Note]: {prompt}"
                        response = "I've added that to the project notes. Please continue sharing the event details or results!"
                except:
                    st.session_state["raw_transcript"] += f"\n\n[Chat Note]: {prompt}"
                    response = "I've added that to the project notes. Tell me more!"
            else:
                st.session_state["raw_transcript"] += f"\n\n[Chat Note]: {prompt}"
                response = "I've added that to the project notes. (Note: Configure API Key for auto-extraction)"

            st.session_state["messages"].append({"role": "assistant", "content": response})
            st.rerun()

        st.markdown("---")
        
        # Secondary: Manual Overrides & Image Upload
        with st.expander(t["manual_entry_title"], expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.session_state["event_date"] = st.text_input(t["date_label"], value=st.session_state["event_date"])
                st.session_state["client_name"] = st.text_input(t["client_label"], value=st.session_state["client_name"])
                st.session_state["project_name"] = st.text_input(t["project_label"], value=st.session_state["project_name"])
            with col2:
                st.session_state["venue"] = st.text_input(t["venue_label"], value=st.session_state["venue"])
                st.session_state["youtube_link"] = st.text_input(t["youtube_link_label"], value=st.session_state["youtube_link"])
            
            st.session_state["raw_transcript"] = st.text_area(t["transcript_label"], value=st.session_state["raw_transcript"], height=150)

            # Image Uploader
            st.subheader(t["image_upload_header"])
            uploaded_files = st.file_uploader(t["image_upload_label"], accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
            
            if uploaded_files:
                mock_urls = []
                for i, uploaded_file in enumerate(uploaded_files):
                    image = Image.open(uploaded_file)
                    if image.width < 1200:
                        st.warning(f"⚠️ Image '{uploaded_file.name}' low res ({image.width}px).")
                    mock_urls.append(f"https://firebean-gallery.com/{st.session_state['project_name'].replace(' ', '_')}_{i+1}.jpg")
                st.session_state["gallery_image_urls"] = ", ".join(mock_urls)
                st.info(f"✅ {len(uploaded_files)} images processed.")

        # GENERATE BUTTON
        if st.button(t["generate_btn"], type="primary", use_container_width=True):
            if not api_key:
                st.error(t["api_key_warning"])
            elif not st.session_state["raw_transcript"]:
                st.error("Please provide a Raw Transcript.")
            else:
                with st.spinner("Firebean Brain Online... Turning Policy into Play..."):
                    try:
                        # Construct the Prompt
                        user_prompt = f"""
                        PROJECT DETAILS:
                        Event Date: {st.session_state['event_date']}
                        Client: {st.session_state['client_name']}
                        Project: {st.session_state['project_name']}
                        Venue: {st.session_state['venue']}
                        Transcript: {st.session_state['raw_transcript']}

                        INSTRUCTIONS:
                        1. Analyze the transcript based on the Firebean Brain Guidelines.
                        2. Select the best 'Category_Who' strictly from: [Government & Public Sector, Lifestyle & Consumer, F&B & Hospitality, Malls & Venues].
                        3. Select the best 'Category_What' strictly from: [Roving Exhibitions, Social & Content, Interactive & Tech, PR & Media, Events & Ceremonies].
                        4. Generate Multilingual PR Copy (EN, CH, JP).
                        5. Generate Social Copy for LinkedIn, FB, IG, Threads, Newsletter based on the specific Platform Writing Rules defined in the system instruction.
                        
                        OUTPUT FORMAT:
                        Return ONLY a valid JSON object with the following keys:
                        category_who, category_what, 
                        title_en, challenge_en, solution_en, result_en,
                        title_ch, challenge_ch, solution_ch, result_ch,
                        title_jp, challenge_jp, solution_jp, result_jp,
                        linkedin_draft, fb_post, ig_caption, threads_post, newsletter_topic,
                        slide_1_cover, slide_2_challenge, slide_3_solution, slide_4_results
                        
                        For slide_1_cover, slide_2_challenge, slide_3_solution, slide_4_results, each should be a list of 3-4 punchy bullet points.
                        """

                        model = genai.GenerativeModel(
                            model_name="gemini-1.5-flash",
                            system_instruction=FIREBEAN_BRAIN_GUIDELINES,
                            generation_config={"response_mime_type": "application/json"}
                        )
                        
                        response = model.generate_content(user_prompt)
                        result_json = json.loads(response.text)

                        # Update Session State
                        for key, value in result_json.items():
                            if key in st.session_state:
                                st.session_state[key] = value
                        
                        # Show Success in Chat
                        success_msg = "✅ Content Generated Successfully! Please review in the Admin Dashboard tab."
                        st.session_state["messages"].append({"role": "assistant", "content": success_msg})
                        with st.chat_message("assistant"):
                            st.markdown(success_msg)
                            st.json(result_json, expanded=False)

                    except Exception as e:
                        st.error(f"Generation Failed: {str(e)}")

    # --- TAB 2: ADMIN DASHBOARD ---
    with tab2:
        st.header(t["admin_header"])
        
        st.markdown(f"### {t['cat_title']}")
        col_cat1, col_cat2, col_cat3 = st.columns(3)
        with col_cat1:
            st.session_state["category_who"] = st.text_input(t["cat_who_label"], value=st.session_state["category_who"])
        with col_cat2:
            st.session_state["category_what"] = st.text_input(t["cat_what_label"], value=st.session_state["category_what"])
        with col_cat3:
            st.session_state["highlight_order"] = st.selectbox(t["highlight_order_label"], ["", "1", "2", "3", "4", "5"], index=0 if st.session_state["highlight_order"] == "" else ["", "1", "2", "3", "4", "5"].index(st.session_state["highlight_order"]))

        st.markdown(f"### {t['pr_copy_title']}")
        tab_en, tab_ch, tab_jp = st.tabs(["English", "Chinese (Trad)", "Japanese"])
        
        with tab_en:
            st.session_state["title_en"] = st.text_input("Title (EN)", value=st.session_state["title_en"])
            st.session_state["challenge_en"] = st.text_area("Challenge (EN)", value=st.session_state["challenge_en"])
            st.session_state["solution_en"] = st.text_area("Solution (EN)", value=st.session_state["solution_en"])
            st.session_state["result_en"] = st.text_area("Result (EN)", value=st.session_state["result_en"])
        
        with tab_ch:
            st.session_state["title_ch"] = st.text_input("Title (CH)", value=st.session_state["title_ch"])
            st.session_state["challenge_ch"] = st.text_area("Challenge (CH)", value=st.session_state["challenge_ch"])
            st.session_state["solution_ch"] = st.text_area("Solution (CH)", value=st.session_state["solution_ch"])
            st.session_state["result_ch"] = st.text_area("Result (CH)", value=st.session_state["result_ch"])

        with tab_jp:
            st.session_state["title_jp"] = st.text_input("Title (JP)", value=st.session_state["title_jp"])
            st.session_state["challenge_jp"] = st.text_area("Challenge (JP)", value=st.session_state["challenge_jp"])
            st.session_state["solution_jp"] = st.text_area("Solution (JP)", value=st.session_state["solution_jp"])
            st.session_state["result_jp"] = st.text_area("Result (JP)", value=st.session_state["result_jp"])

        st.markdown(f"### {t['social_title']}")

        st.session_state["linkedin_draft"] = st.text_area("LinkedIn Draft (Institutional Cool)", value=st.session_state["linkedin_draft"], height=200)
        st.session_state["fb_post"] = st.text_area("Facebook Post (Weekend Planner)", value=st.session_state["fb_post"], height=200)
        st.session_state["ig_caption"] = st.text_area("Instagram Caption (Lifestyle Curator)", value=st.session_state["ig_caption"], height=200)
        st.session_state["threads_post"] = st.text_area("Threads Post (Unfiltered)", value=st.session_state["threads_post"], height=150)
        st.session_state["newsletter_topic"] = st.text_input("Newsletter Topic", value=st.session_state["newsletter_topic"])

        st.markdown("---")
        if st.button(t["approve_btn"], type="primary"):
            # Prepare Payload
            payload = {
                "event_date": st.session_state["event_date"],
                "client_name": st.session_state["client_name"],
                "project_name": st.session_state["project_name"],
                "venue": st.session_state["venue"],
                "category_who": st.session_state["category_who"],
                "category_what": st.session_state["category_what"],
                "highlight_order": st.session_state["highlight_order"],
                "raw_transcript": st.session_state["raw_transcript"],
                "youtube_link": st.session_state["youtube_link"],
                "gallery_image_urls": st.session_state["gallery_image_urls"],
                "project_drive_folder": st.session_state["project_drive_folder"],
                "best_image_url": st.session_state["best_image_url"],
                "client_logo_url": st.session_state["client_logo_url"],
                "youtube_embed_code": st.session_state["youtube_embed_code"],
                "title_en": st.session_state["title_en"],
                "challenge_en": st.session_state["challenge_en"],
                "solution_en": st.session_state["solution_en"],
                "result_en": st.session_state["result_en"],
                "title_ch": st.session_state["title_ch"],
                "challenge_ch": st.session_state["challenge_ch"],
                "solution_ch": st.session_state["solution_ch"],
                "result_ch": st.session_state["result_ch"],
                "title_jp": st.session_state["title_jp"],
                "challenge_jp": st.session_state["challenge_jp"],
                "solution_jp": st.session_state["solution_jp"],
                "result_jp": st.session_state["result_jp"],
                "linkedin_draft": st.session_state["linkedin_draft"],
                "fb_post": st.session_state["fb_post"],
                "ig_caption": st.session_state["ig_caption"],
                "threads_post": st.session_state["threads_post"],
                "newsletter_topic": st.session_state["newsletter_topic"],
                "slide_1_cover": st.session_state["slide_1_cover"],
                "slide_2_challenge": st.session_state["slide_2_challenge"],
                "slide_3_solution": st.session_state["slide_3_solution"],
                "slide_4_results": st.session_state["slide_4_results"]
            }
            
            # Send Webhook
            webhook_url = "https://script.google.com/macros/s/AKfycbxgqW5gtfhyH2bgCl1G-zpmv8yTu0IzyAblqxumzT0hP0efwOl-hbL4MN6S9Du-Y3YP/exec"
            try:
                with st.spinner("Syncing to Firebean Database..."):
                    response = requests.post(webhook_url, json=payload)
                    if response.status_code == 200:
                        st.success(t["save_success"])
                        st.balloons()
                    else:
                        st.error(f"{t['save_error']} {response.status_code}")
            except Exception as e:
                st.error(f"{t['conn_error']} {str(e)}")

    # --- TAB 3: SLIDE PREVIEW ---
    with tab3:
        st.header(t["tab3_title"])
        
        def render_slide(title, content_list, slide_number):
            st.markdown(f"<div class='neu-container' style='min-height: 250px; border-left: 5px solid #F27D26; margin-bottom: 20px;'>", unsafe_allow_html=True)
            st.markdown(f"#### Slide {slide_number}: {title}")
            if content_list:
                for item in content_list:
                    st.markdown(f"- {item}")
            else:
                st.info("No content generated for this slide yet.")
            st.markdown("</div>", unsafe_allow_html=True)

        render_slide("Cover", st.session_state["slide_1_cover"], 1)
        render_slide("Challenge", st.session_state["slide_2_challenge"], 2)
        render_slide("Solution", st.session_state["slide_3_solution"], 3)
        render_slide("Results", st.session_state["slide_4_results"], 4)

if __name__ == "__main__":
    main()
