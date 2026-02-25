import streamlit as st
import google.generativeai as genai
import io
import base64
import json
import requests
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from datetime import datetime

# --- 1. 核心配置與 API Key 池 (鎖死同步連結) ---
# 這是你原本打通的 GAS 連結，負責將數據寫入 Master DB A-T 欄 [cite: 3, 6, 9-16]
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwLR9MVr4rNgCQeXd2zGq43_F3ncsml_t7IP4OkjqBNtdNiv0ETitiuzx4oif3T0tCZ/exec"

API_KEYS_POOL = [
    "AIzaSyA-5qXWjtzlUWP0IDMVUByMXdbylt8rTSA",
    "AIzaSyCVuoSuWV3tfGCu2tjikCkMOVRWCBFne20",
    "AIzaSyCZKtjLqN4FUQ76c3DYoDW20tTkFki_Rxk"
]

# 鎖死選項設定
WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# 鎖死核心 PR DNA 與 生成規範
FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
Motto: 'Turn Policy into Play'.

STRICT RULES:
1. LANGUAGES: Output ONLY in English (EN), Traditional Chinese (TC), and Japanese (JP). NO Simplified Chinese.
2. LENGTH: Challenge and Solution sections MUST be concise (50-100 words).
3. STYLE: LinkedIn/Slides (Professional), IG/Threads (Canto-slang), Website (Trilingual).
4. BRANDING: Naturally include "Firebean PR" and relevant hashtags.
"""

# --- 2. 核心調試與 SDK 智能輪詢引擎 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False, dynamic_sys_prompt=None):
    all_keys = API_KEYS_POOL
    model_name = "gemini-2.0-flash" # 鎖定穩定版本
    sys_instruction = dynamic_sys_prompt if dynamic_sys_prompt else FIREBEAN_SYSTEM_PROMPT

    for idx, key in enumerate(all_keys):
        try:
            genai.configure(api_key=key)
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json" if is_json else "text/plain"
            )
            model = genai.GenerativeModel(model_name=model_name, system_instruction=sys_instruction)
            contents = [prompt]
            if image_file: contents.append(image_file)
            response = model.generate_content(contents, generation_config=generation_config)
            if response and response.text:
                return response.text
        except Exception as e:
            log_debug(f"Key #{idx+1} Error: {str(e)}", "warning")
            continue
    return None

# --- 3. 影像與 Logo 處理重要元素 ---

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
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log_debug(f"Logo Error: {str(e)}", "error")
        return ""

def manna_ai_enhance(image_file):
    log_debug(f"AI Vision Processing: {image_file.name}")
    try:
        raw_img = Image.open(image_file)
        img = ImageOps.exif_transpose(raw_img).convert("RGB")
        img_enhanced = ImageEnhance.Contrast(img).enhance(1.15)
        call_gemini_sdk("Analyze this institutional project photo.", image_file=img)
        return img_enhanced
    except Exception:
        return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

# --- 4. 訪談邏輯與 UI 狀態鎖定 ---

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "ai_content": {}, "project_photos": [], "hero_index": 0,
        "processed_photos": {}, "logo_white": "", "logo_black": "", "debug_logs": [],
        "messages": [{"role": "assistant", "content": "Firebean Brain Online. 我係 PR Director。可唔可以講下今次項目 Client 遇到最大嘅 Challenge 係咩？定係個主題太悶難吸客？"}]
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def get_proactive_chatbot_prompt():
    """鎖定反問引導邏輯"""
    return f"""{FIREBEAN_SYSTEM_PROMPT}
    You are a Proactive Senior PR Director. INTERVIEW the user. 
    If information is missing, use PROBING QUESTIONS (e.g., offer scenarios or multiple choices). 
    Do not just say "Got it". Ask for ONE missing piece at a time.
    """

# --- 5. 同步至 Master DB (鎖死 A-T 欄映射) ---

def sync_to_master_ecosystem():
    if not st.session_state.ai_content:
        st.error("請先生成文案！")
        return

    with st.spinner("🚀 同步數據至 Master DB A-T 欄..."):
        try:
            ai = st.session_state.ai_content
            payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # A 欄
                "client_name": st.session_state.client_name,               # B 欄
                "project_name": st.session_state.project_name,             # C 欄
                "event_date": f"{st.session_state.event_year} {st.session_state.event_month}", # D 欄
                "venue": st.session_state.venue,                           # E 欄
                "category_who": ", ".join(st.session_state.who_we_help),   # F 欄
                "category_what": ", ".join(st.session_state.what_we_do),   # G 欄
                "scope_of_work": ", ".join(st.session_state.scope_of_word), # H 欄
                "youtube_link": st.session_state.youtube_link,             # I 欄
                "challenge": ai.get("6_website", {}).get("tc", {}).get("content", ""), # J 欄
                "solution": ai.get("6_website", {}).get("tc", {}).get("content", ""),  # K 欄
                "ai_content": ai # 包含 L-S 欄的所有多平台風格文案 [cite: 9-14]
            }
            res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=30)
            if res.status_code == 200:
                st.balloons(); st.success("✅ 同步成功！Status 已設為 Synced。")
        except Exception as e:
            st.error(f"Sync Failed: {str(e)}")

# --- 6. Main App 介面 ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    
    # Header & 12 維度 Progress Bar
    filled = sum([1 for f in ["client_name", "project_name", "venue", "challenge", "solution", "youtube_link"] if st.session_state[f]])
    percent = int((filled / 12) * 100) # 簡略計算
    st.sidebar.metric("Master DB Progress", f"{percent}%")

    tab1, tab2 = st.tabs(["💬 Chat & Data", "🚀 Generation & Sync"])

    with tab1:
        # Logo & Info 區域 (略，保持原有 UI)
        st.subheader("🤖 PR Director 智能訪談 (引導模式)")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.write(m["content"])
            
        if p := st.chat_input("向 PR Director 匯報..."):
            st.session_state.messages.append({"role": "user", "content": p})
            res = call_gemini_sdk(p, dynamic_sys_prompt=get_proactive_chatbot_prompt())
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.rerun()

    with tab2:
        if st.button("🪄 生成六大平台文案 (Follow DNA)"):
            prompt = "Generate JSON for all 6 platforms (Slide, FB, IG, Threads, LinkedIn, Website EN/TC/JP)."
            res_json = call_gemini_sdk(prompt, is_json=True)
            if res_json: st.session_state.ai_content = json.loads(res_json)
            
        if st.button("🚀 Confirm & Sync to Master Ecosystem"):
            sync_to_master_ecosystem()

if __name__ == "__main__":
    main()
