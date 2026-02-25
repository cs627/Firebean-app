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

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw5Bf3CsEYZJCEVzgzS_pSwg8y0B69iHLDywgZyz45ctsZTShe1YxRiTTKGjiMc1HFe/exec"
API_KEYS_POOL = st.secrets.get("API_KEYS", [])

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# 鎖死核心 DNA 與 退出機制
FIREBEAN_SYSTEM_PROMPT = """
Identity: 'Firebean Brain' (Institutional Cool). 
Motto: 'Turn Policy into Play'. 
Strategy: 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).

[STRICT INTERVIEW RULES]
1. 你現在的任務是獲取 Case Study 所需的 Challenge 和 Solution 深度。
2. **退出機制**：一旦用戶提供了具體的描述，或者當前進度已接近圓滿，你必須停止追問，並輸出最終的 JSON 格式。
3. **嚴禁循環**：如果用戶表現出不耐煩，或直接要求生成，請立即結束訪談並輸出 JSON。
4. 語言：僅限 EN, TC, JP。嚴禁簡體中文。每段內容鎖定 50-100 字。
"""

# --- 2. 核心功能 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False, dynamic_sys_prompt=None):
    sys_instruction = dynamic_sys_prompt if dynamic_sys_prompt else FIREBEAN_SYSTEM_PROMPT
    for idx, key in enumerate(API_KEYS_POOL):
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name="gemini-2.0-flash", system_instruction=sys_instruction)
            config = genai.types.GenerationConfig(response_mime_type="application/json" if is_json else "text/plain")
            contents = [prompt]
            if image_file: contents.append(image_file)
            response = model.generate_content(contents, generation_config=config)
            if response and response.text: return response.text
        except Exception as e:
            log_debug(f"Key #{idx+1} Error: {str(e)}", "warning")
            continue
    return None

def standardize_logo(logo_file):
    try:
        raw = Image.open(logo_file)
        img = ImageOps.exif_transpose(raw).convert("RGBA")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

def manna_ai_enhance(image_file):
    try:
        raw_img = Image.open(image_file)
        img = ImageOps.exif_transpose(raw_img).convert("RGB")
        return ImageEnhance.Contrast(img).enhance(1.15)
    except: return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

# --- 3. UI 樣式 ---

def apply_styles():
    st.markdown("""
        <style>
        .stApp { background-color: #E0E5EC; color: #2D3436; }
        .neu-card { background: #E0E5EC; border-radius: 20px; box-shadow: 10px 10px 20px #bec3c9, -10px -10px 20px #ffffff; padding: 20px; margin-bottom: 20px; }
        .hero-border { border: 4px solid #FF0000; border-radius: 12px; }
        .debug-terminal { background: #1E1E1E; color: #00FF00; padding: 10px; font-family: monospace; font-size: 11px; }
        </style>
    """, unsafe_allow_html=True)

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "youtube_link": "", "messages": [{"role": "assistant", "content": "Director Online. 請分享下今次個 Challenge 係咩？"}],
        "project_photos": [], "hero_index": 0, "processed_photos": {}, "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": []
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 計算 12 維度進度
    score_items = ["client_name", "project_name", "venue", "challenge", "solution", "youtube_link"]
    filled = sum([1 for f in score_items if st.session_state[f]])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white or st.session_state.logo_black else 0)
    filled += (1 if len(st.session_state.project_photos) >= 4 else 0) + (1 if st.session_state.ai_content else 0)
    percent = int((filled / 12) * 100)

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    st.progress(filled / 12, text=f"Master DB Progress: {percent}%")

    tab1, tab2 = st.tabs(["💬 Data Collector", "📋 Generation & Sync"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        # 基本資料輸入區 (略，保持原有 UI)
        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.youtube_link = b3.text_input("YouTube Link", st.session_state.youtube_link)
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean Director (Interview Mode)")
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])
            
            if p := st.chat_input("向 PR Director 匯報細節..."):
                st.session_state.messages.append({"role": "user", "content": p})
                
                # 改進的 Prompt：告訴 AI 填寫進度，減少無效追問
                context_prompt = f"""
                Current Progress: {percent}% filled. 
                Existing Challenge: {st.session_state.challenge}
                Existing Solution: {st.session_state.solution}
                User Input: {p}
                
                If you have enough information for a professional 50-100 word Case Study, 
                output the final JSON now. Otherwise, ask ONE focused follow-up question.
                """
                res = call_gemini_sdk(context_prompt)
                
                # 自動偵測 JSON 輸出
                if "{" in res and "}" in res:
                    try:
                        st.session_state.ai_content = json.loads(res[res.find("{"):res.rfind("}")+1])
                        st.session_state.messages.append({"role": "assistant", "content": "✅ 資料已圓滿，文案已生成！請前往 Tab 2 確認。"})
                    except: st.session_state.messages.append({"role": "assistant", "content": res})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": res})
                st.rerun()
            
            # 🔥 新增：強制結束按鈕
            if st.button("⏹️ 資料已夠，結束訪談並強制生成"):
                with st.spinner("🧠 正在根據現有資料生成最終文案..."):
                    res = call_gemini_sdk("FORCE GENERATE FINAL JSON NOW based on current context.", is_json=True)
                    if res: st.session_state.ai_content = json.loads(res); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            # 📸 相片區 (略，保持原有 UI)
            files = st.file_uploader("Upload 4+ Photos", accept_multiple_files=True)
            if files: st.session_state.project_photos = files

    with tab2:
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync to Master Ecosystem"):
                payload = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "client_name": st.session_state.client_name,
                    "project_name": st.session_state.project_name,
                    "youtube_link": st.session_state.youtube_link,
                    "ai_content": st.session_state.ai_content
                }
                res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=30)
                if res.status_code == 200: st.balloons(); st.success("✅ 同步 Master DB 成功！")
        else:
            st.info("請先在 Tab 1 完成訪談或按「強制生成」按鈕。")

if __name__ == "__main__":
    main()
