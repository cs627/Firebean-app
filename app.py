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
    st.session_state.open_question_ans = "將 20 個通用診斷問題轉化為一套連貫、引人入勝且
