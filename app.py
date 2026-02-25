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

# --- 1. 核心配置 (鎖定同步連結) ---
# 鎖死 A-T 欄映射同步連結 [cite: 3, 6, 9-16]
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw5Bf3CsEYZJCEVzgzS_pSwg8y0B69iHLDywgZyz45ctsZTShe1YxRiTTKGjiMc1HFe/exec"

# 🔑 從 Streamlit Secrets 讀取 API Key 池 (防止 403 報錯)
# 請在 Settings -> Secrets 貼入: API_KEYS = ["Key1", "Key2", "Key3"]
API_KEYS_POOL = st.secrets.get("API_KEYS", [])

# 鎖定 PR DNA 核心指令
FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
LinkedIn/Slides: Professional Business English. IG/Threads: Canto-slang. Website: Trilingual (EN, TC, JP).
Strictly NO Simplified Chinese. All Challenge/Solution sections must be 50-100 words.
Motto: 'Turn Policy into Play'.
"""

# --- 2. 核心調試與 SDK 智能輪詢引擎 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False, dynamic_sys_prompt=None):
    if not API_KEYS_POOL:
        log_debug("🚨 找不到 API Keys！請檢查 Secrets 設定。", "error")
        return None

    model_name = "gemini-2.0-flash"
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
            err = str(e)
            if "429" in err: log_debug(f"Key #{idx+1} 爆配額 (429)，切換中...", "warning")
            elif "403" in err: log_debug(f"Key #{idx+1} 遭停用 (403)！", "error")
            continue
    return None

# --- 3. 影像處理與 UI 組件 (鎖死細節) ---

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
        log_debug(f"Logo Fix Error: {str(e)}", "error")
        return ""

def manna_ai_enhance(image_file):
    log_debug(f"Vision Processing: {image_file.name}")
    with st.spinner("🚀 Manna AI 校正轉向並同步視角..."):
        try:
            raw_img = Image.open(image_file)
            img = ImageOps.exif_transpose(raw_img).convert("RGB")
            img_enhanced = ImageEnhance.Contrast(img).enhance(1.15)
            call_gemini_sdk("Analyze this photo.", image_file=img)
            return img_enhanced
        except Exception:
            return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

# --- 4. 初始化與同步邏輯 (對接 Master DB) ---

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "ai_content": {}, "project_photos": [], "hero_index": 0,
        "processed_photos": {}, "logo_white": "", "logo_black": "", "debug_logs": [],
        "messages": [{"role": "assistant", "content": "Firebean Director Online. 聽落個項目好有潛力，可唔可以分享下最初 Client 遇到最大嘅 Challenge 係咩？"}]
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def sync_to_master_db(ai_results):
    """同步至 Google Sheet A-T 欄位 [cite: 1, 9-15]"""
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

# --- 5. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    
    # 鎖定 12 維度進度條
    score_items = ["client_name", "project_name", "venue", "challenge", "solution", "youtube_link"]
    filled = sum([1 for f in score_items if st.session_state[f]])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white and st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0) + (1 if st.session_state.ai_content else 0)
    percent = int((filled / 12) * 100)

    # UI Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.write(f"### Master DB Progress: {percent}%")

    tab1, tab2 = st.tabs(["💬 Data & Chatbot", "🚀 Sync to Ecosystem"])

    with tab1:
        # 訪談與資料收集
        st.subheader("🤖 Firebean Director (引導訪談)")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.write(m["content"])
        if p := st.chat_input("匯報細節..."):
            st.session_state.messages.append({"role": "user", "content": p})
            res = call_gemini_sdk(f"History: {st.session_state.messages[-3:]}\nUser: {p}")
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.rerun()

    with tab2:
        # 生成與同步 A-T 欄 [cite: 1, 9-15]
        if st.button("🪄 一鍵生成六路文案 (50-100字)"):
            prompt = "Generate JSON for Slide, LinkedIn, FB, Threads, IG, Website (EN, TC, JP)."
            res_json = call_gemini_sdk(prompt, is_json=True)
            if res_json: st.session_state.ai_content = json.loads(res_json)
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync to Master Ecosystem"):
                if sync_to_master_db(st.session_state.ai_content):
                    st.balloons(); st.success("✅ 同步至 Master DB A-T 欄成功！")

    # Debug 終端
    with st.expander("🛠️ Debug Terminal"):
        for l in reversed(st.session_state.debug_logs):
            st.write(f"[{l['time']}] {l['msg']}")

if __name__ == "__main__":
    main()
