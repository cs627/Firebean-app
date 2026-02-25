import streamlit as st
import requests
import io
import base64
import time
import json
import traceback
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from datetime import datetime

# --- 1. 定義環境 URL 與 選項清單 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwLR9MVr4rNgCQeXd2zGq43_F3ncsml_t7IP4OkjqBNtdNiv0ETitiuzx4oif3T0tCZ/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbya_pl6h99zY_LrURojCL86c20NwxdeW6V9bhCXqgPjJdz2NVPgeFThthcR6gfw0d1P/exec"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Follow 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
LinkedIn/Slides: EN only. IG/Threads: Canto-slang. Website: Trilingual.
Motto: 'Turn Policy into Play'.
"""

# --- 2. 核心 API 功能與 Debug 系統 ---

def log_debug(msg, type="info"):
    """將消息推送到 Debug Console"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({
        "time": timestamp,
        "msg": msg,
        "type": type
    })

def call_gemini_rest(prompt, image_b64=None, model="gemini-2.5-flash-preview-09-2025"):
    """REST API 調用 Gemini"""
    api_key = "" # 執行環境自動注入
    
    if image_b64:
        model_id = "gemini-2.5-flash-image-preview"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": image_b64}}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]}
        }
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": FIREBEAN_SYSTEM_PROMPT}]}
        }

    for i in range(5):
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                log_debug(f"Gemini API Success (Attempt {i+1})", "success")
                return response.json()
            else:
                log_debug(f"API Error {response.status_code}: {response.text[:100]}", "error")
            time.sleep(2**i)
        except Exception as e:
            log_debug(f"Connection Failed: {str(e)}", "error")
            time.sleep(2**i)
    return None

def manna_ai_enhance(image_file):
    """Manna AI Generative Expander: 虛擬影像擴展"""
    log_debug("Starting Generative Outpainting...")
    with st.spinner("🚀 Manna AI 正在進行虛擬影像擴展..."):
        try:
            raw_img = Image.open(image_file)
            img = ImageOps.exif_transpose(raw_img).convert("RGB")
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            b64_img = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            prompt = "Generatively outpaint this image into a cinematic 16:9 landscape banner. Naturally extend the background on both sides."
            
            result = call_gemini_rest(prompt, image_b64=b64_img)
            if result:
                parts = result.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                for part in parts:
                    if 'inlineData' in part:
                        img_data = base64.b64decode(part['inlineData']['data'])
                        log_debug("Image expansion completed successfully.", "success")
                        return Image.open(io.BytesIO(img_data))
            
            log_debug("Outpainting failed to return image data.", "warning")
            return img
        except Exception as e:
            log_debug(f"Enhance Error: {traceback.format_exc()}", "error")
            return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

def standardize_logo(logo_file, target_size=(800, 400), padding=40):
    """Logo 標準化處理"""
    log_debug(f"Standardizing logo: {logo_file.name}")
    try:
        img = ImageOps.exif_transpose(Image.open(logo_file)).convert("RGBA")
        bbox = img.getbbox()
        if bbox: img = img.crop(bbox)
        inner_w, inner_h = target_size[0] - (padding * 2), target_size[1] - (padding * 2)
        img.thumbnail((inner_w, inner_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, img)
        buf = io.BytesIO()
        canvas.save(buf, format="PNG", optimize=True)
        log_debug("Logo standardized successfully.", "success")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log_debug(f"Logo Standardization Error: {str(e)}", "error")
        return ""

# --- 3. UI 視覺樣式 ---

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 25px; box-shadow: 12px 12px 24px #bec3c9, -12px -12px 24px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.4); border-radius: 12px; }
        .ai-status-tag { background: #FF3333; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 800; display: inline-block; margin-bottom: 5px; }
        /* Debug Bar Styling */
        .debug-bar { background: #2D3436; color: #00FF00; padding: 15px; border-top: 5px solid #FF0000; font-family: 'Courier New', monospace; font-size: 12px; border-radius: 15px 15px 0 0; }
        .debug-msg-error { color: #FF5555; }
        .debug-msg-success { color: #55FF55; }
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
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "messages": [{"role": "assistant", "content": "Firebean Brain Online."}], 
        "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, "logo_white": "", "logo_black": "",
        "debug_logs": [] # 調試日誌
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# --- 4. Main App 邏輯 ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # Progress 計算 (11 維度)
    filled = sum([1 for f in ["client_name", "project_name", "venue", "challenge", "solution"] if st.session_state[f]])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white and st.session_state.logo_black else 0) 
    filled += (1 if st.session_state.project_photos else 0) + (1 if st.session_state.ai_content else 0)
    percent = int((filled / 11) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Data Collector & Chatbot", "📋 Ecosystem Sync & AI Content"])

    with tab1:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Client Logo Standardizer")
        lc1, lc2 = st.columns(2)
        with lc1:
            up_black = st.file_uploader("Upload Black Logo (PNG)", type=['png'], key="logo_b")
            if up_black and st.button("📏 Standardize Black"):
                st.session_state.logo_black = standardize_logo(up_black)
        with lc2:
            up_white = st.file_uploader("Upload White Logo (PNG)", type=['png'], key="logo_w")
            if up_white and st.button("📏 Standardize White"):
                st.session_state.logo_white = standardize_logo(up_white)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Project Basic Information")
        b1, b2, b3_y, b3_m, b4 = st.columns([1, 1, 0.6, 0.4, 1])
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.event_year = b3_y.selectbox("Year", YEARS, index=YEARS.index(st.session_state.event_year))
        st.session_state.event_month = b3_m.selectbox("Month", MONTHS, index=MONTHS.index(st.session_state.event_month))
        st.session_state.venue = b4.text_input("Venue", st.session_state.venue)
        
        c1, c2, c3 = st.columns(3)
        st.session_state.who_we_help = c1.multiselect("👥 Who we help", WHO_WE_HELP_OPTIONS, default=st.session_state.who_we_help)
        st.session_state.what_we_do = c2.multiselect("🚀 What we do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do)
        st.session_state.scope_of_word = c3.multiselect("🛠️ Scope", SOW_OPTIONS, default=st.session_state.scope_of_word)
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean AI Chatbot")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            if p := st.chat_input("詢問細節..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                result = call_gemini_rest(f"Context SOW: {st.session_state.scope_of_word}\nInquiry: {p}")
                if result:
                    reply = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "AI Timeout.")
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Manna AI Outpainting Gallery")
            files = st.file_uploader("Upload Photos", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                hero_choice = st.radio("🌟 Hero?", [f"P{i+1}" for i in range(len(files))], horizontal=True)
                st.session_state.hero_index = int(hero_choice[1:]) - 1
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        is_proc = i in st.session_state.processed_photos
                        if is_proc: st.markdown('<div class="ai-status-tag">✨ AI READY</div>', unsafe_allow_html=True)
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
        st.header("📋 Sync to Ecosystem")
        st.session_state.challenge = st.text_area("Challenge (EN)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution (EN)", st.session_state.solution)
        
        if st.button("🪄 生成五路文案"):
            log_debug("Generating AI Copywriting...")
            prompt = f"Project: {st.session_state.project_name}\nChallenge: {st.session_state.challenge}\nGenerate JSON: slide_en, linkedin_en, facebook_tc, ig_threads_oral, web_en, web_tc, web_jp."
            result = call_gemini_rest(prompt)
            if result:
                try:
                    text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "")
                    st.session_state.ai_content = json.loads(text[text.find('{'):text.rfind('}')+1])
                    st.success("✅ AI 文案生成完成！")
                except Exception as e:
                    log_debug(f"JSON Parse Error: {str(e)}", "error")

        if st.session_state.ai_content: st.json(st.session_state.ai_content)

        if st.button("🚀 Confirm & Sync"):
            log_debug("Syncing to Master Database...")
            b64_imgs = []
            for i in range(len(st.session_state.project_photos)):
                img = st.session_state.processed_photos.get(i, ImageOps.exif_transpose(Image.open(st.session_state.project_photos[i])))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=85)
                b64_imgs.append(base64.b64encode(buf.getvalue()).decode())
            
            payload = {
                "client_name": st.session_state.client_name, "project_name": st.session_state.project_name, "event_date": st.session_state.event_date,
                "venue": st.session_state.venue, "scope_of_work": ", ".join(st.session_state.scope_of_word),
                "ai": st.session_state.ai_content, "images": b64_imgs,
                "logo_white": st.session_state.logo_white, "logo_black": st.session_state.logo_black
            }
            try:
                res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=40)
                if "Success" in res.text:
                    st.balloons(); st.success("✅ 同步成功！")
                    log_debug("Sync completed successfully.", "success")
                else:
                    log_debug(f"Sync failed: {res.text}", "error")
            except Exception as e:
                log_debug(f"Sync error: {str(e)}", "error")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 5. Debug Console Bottom Bar ---
    st.markdown("---")
    with st.expander("🛠️ Firebean Brain Debug Terminal", expanded=False):
        if not st.session_state.debug_logs:
            st.write("No logs recorded.")
        for log in reversed(st.session_state.debug_logs):
            color_class = f"debug-msg-{log['type']}"
            st.markdown(f"<div class='debug-bar {color_class}'>[{log['time']}] {log['msg']}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
