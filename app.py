import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import traceback
import requests
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from datetime import datetime

# --- 1. 核心配置與 API Key 池 ---
# 鎖定同步連結：Master DB A-T 欄 
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw5Bf3CsEYZJCEVzgzS_pSwg8y0B69iHLDywgZyz45ctsZTShe1YxRiTTKGjiMc1HFe/exec"

# 🔑 從 Streamlit Secrets 讀取 API Key (防止 403 報錯)
API_KEYS_POOL = st.secrets.get("API_KEYS", [])

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# 鎖死核心 PR DNA
FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
LinkedIn/Slides: Professional Business English. IG/Threads: Canto-slang. Website: Trilingual (EN, TC, JP).
Motto: 'Turn Policy into Play'. 
Strictly NO Simplified Chinese. All Challenge/Solution sections must be 50-100 words.
"""

# --- 2. 核心 SDK 引擎與影像處理 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False, dynamic_sys_prompt=None):
    if not API_KEYS_POOL:
        log_debug("🚨 找不到 API Keys！請檢查 Secrets 設定。", "error")
        return None
    model_name = "gemini-2.5-flash"
    sys_instruction = dynamic_sys_prompt if dynamic_sys_prompt else FIREBEAN_SYSTEM_PROMPT
    for idx, key in enumerate(API_KEYS_POOL):
        try:
            log_debug(f"Attempting API with Key #{idx+1}...", "info")
            genai.configure(api_key=key)
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json" if is_json else "text/plain"
            )
            model = genai.GenerativeModel(model_name=model_name, system_instruction=sys_instruction)
            contents = [prompt]
            if image_file: contents.append(image_file)
            response = model.generate_content(contents, generation_config=generation_config)
            if response and response.text:
                log_debug(f"Success with Key #{idx+1}!", "success")
                return response.text
        except Exception as e:
            log_debug(f"Key #{idx+1} Error: {str(e)}", "warning")
            continue
    return None

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
    except Exception: return ""

def manna_ai_enhance(image_file):
    log_debug(f"Vision Processing for: {image_file.name}")
    with st.spinner("🚀 Manna AI 正在校正轉向並同步視角..."):
        try:
            raw_img = Image.open(image_file)
            img = ImageOps.exif_transpose(raw_img).convert("RGB")
            img_enhanced = ImageEnhance.Contrast(img).enhance(1.15)
            call_gemini_sdk("Analyze this photo.", image_file=img)
            return img_enhanced
        except Exception: return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

# --- 3. UI 視覺與同步邏輯 ---

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 25px; box-shadow: 12px 12px 24px #bec3c9, -12px -12px 24px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.4); border-radius: 12px; }
        .debug-terminal { background: #1E1E1E; color: #00FF00; padding: 12px; font-family: 'Courier New', monospace; font-size: 11px; }
        </style>
    """, unsafe_allow_html=True)

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "messages": [{"role": "assistant", "content": "Firebean Brain Online. 請分享下今次個 Challenge 係咩？"}],
        "project_photos": [], "hero_index": 0, "processed_photos": {}, "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": []
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def sync_to_master_db(ai_results):
    """鎖死 A-T 欄同步映射邏輯"""
    try:
        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "client_name": st.session_state.client_name,
            "project_name": st.session_state.project_name,
            "event_date": f"{st.session_state.event_year} {st.session_state.event_month}",
            "venue": st.session_state.venue,
            "category_who": ", ".join(st.session_state.who_we_help),
            "category_what": ", ".join(st.session_state.what_we_do),
            "scope_of_work": ", ".join(st.session_state.scope_of_word),
            "youtube_link": st.session_state.youtube_link,
            "challenge": ai_results.get("6_website", {}).get("tc", {}).get("content", ""),
            "solution": ai_results.get("6_website", {}).get("tc", {}).get("content", ""),
            "ai_content": ai_results
        }
        res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=30)
        return res.status_code == 200
    except Exception as e:
        log_debug(f"Sync failed: {str(e)}", "error")
        return False

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 進度計算 (12 維度)
    score_items = ["client_name", "project_name", "venue", "challenge", "solution", "youtube_link"]
    filled = sum([1 for f in score_items if st.session_state[f]])
    percent = int((filled / 12) * 100)

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    st.write(f"### Master DB Progress: {percent}%")

    tab1, tab2 = st.tabs(["💬 Data Collector & Chatbot", "📋 Generation & Sync"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🤖 Firebean Director (Interview)")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.write(m["content"])
        if p := st.chat_input("向 PR Director 匯報..."):
            st.session_state.messages.append({"role": "user", "content": p})
            res = call_gemini_sdk(p)
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        if st.button("🪄 一鍵生成六大平台文案 (Follow DNA)"):
            with st.spinner("🧠 正在生成三語文案 (精簡 50-100 字)..."):
                prompt = "Generate Master JSON for Slides, Socials, and Website (Trilingual, 50-100 words)."
                res_json = call_gemini_sdk(prompt, is_json=True)
                if res_json: 
                    st.session_state.ai_content = json.loads(res_json)
                    st.success("✅ 生成成功！")
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync to Master Ecosystem"):
                if sync_to_master_db(st.session_state.ai_content):
                    st.balloons(); st.success("✅ 同步 Master DB 成功！")

    # Debug Terminal
    with st.expander("🛠️ Debug Terminal"):
        if st.session_state.debug_logs:
            for l in reversed(st.session_state.debug_logs):
                st.markdown(f"<div class='debug-terminal'>[{l['time']}] {l['msg']}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
