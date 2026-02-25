import streamlit as st
import requests
import io
import base64
import time
import json
import traceback
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from datetime import datetime

# --- 1. 配置與 URL ---
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
Output Format: Professional business English for Slides/LinkedIn. Canto-slang for social media.
"""

# --- 2. 核心調試與 API 引擎 ---

def log_debug(msg, type="info"):
    """永久調試日誌系統：確保在底部 Terminal 顯示所有過程"""
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_rest(prompt, image_b64=None, model="gemini-2.5-flash-preview-09-2025"):
    """使用 REST API 調用 Gemini，修復 403 報錯並支持影像擴展"""
    # 從 Secrets 讀取 Key，解決 Unregistered Caller 問題
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        log_debug("GEMINI_API_KEY missing in Streamlit Secrets!", "error")
        return None
    
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
                log_debug(f"Gemini API ({model}) Success", "success")
                return response.json()
            else:
                log_debug(f"API Error {response.status_code}: {response.text[:100]}", "error")
            time.sleep(2**i)
        except Exception as e:
            log_debug(f"Request failed: {str(e)}", "error")
            time.sleep(2**i)
    return None

def standardize_logo(logo_file, target_size=(800, 400), padding=40):
    """修復旋轉問題並將 Logo 標準化置中"""
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
        
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        log_debug(f"Logo {logo_file.name} standardized.", "success")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log_debug(f"Logo Error: {str(e)}", "error")
        return ""

def manna_ai_enhance(image_file):
    """真正的 AI 影像擴展 (Outpainting) + 修正直相旋轉"""
    log_debug(f"Starting AI Outpainting for {image_file.name}...")
    with st.spinner("🚀 Manna AI 正在進行虛擬影像擴展..."):
        try:
            # 關鍵修正：解決直相旋轉問題
            img = ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")
            
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            b64_img = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            prompt = "Generatively outpaint this image into a cinematic 16:9 landscape banner. Naturally extend the background to fill left and right sides. Maintain photography style."
            
            result = call_gemini_rest(prompt, image_b64=b64_img)
            if result:
                parts = result.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                for part in parts:
                    if 'inlineData' in part:
                        img_data = base64.b64decode(part['inlineData']['data'])
                        log_debug("AI Expansion Completed", "success")
                        return Image.open(io.BytesIO(img_data))
            
            log_debug("AI outpainting timed out or empty response.", "warning")
            return img
        except Exception:
            log_debug(f"Enhance Error: {traceback.format_exc()}", "error")
            return ImageOps.exif_transpose(Image.open(image_file)).convert("RGB")

# --- 3. UI 樣式組件 ---

def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 25px; box-shadow: 12px 12px 24px #bec3c9, -12px -12px 24px #ffffff; padding: 25px; margin-bottom: 20px; }
        .hero-border { border: 4px solid #FF0000; box-shadow: 0 0 15px rgba(255,0,0,0.4); border-radius: 12px; }
        .ai-status-tag { background: #FF3333; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 800; display: inline-block; margin-bottom: 5px; }
        .debug-terminal { background: #1E1E1E; color: #00FF00; padding: 12px; font-family: 'Courier New', monospace; font-size: 11px; border-top: 4px solid #FF0000; border-radius: 10px 10px 0 0; max-height: 200px; overflow-y: auto; }
        .debug-success { color: #00FF00; }
        .debug-error { color: #FF5555; }
        </style>
    """, unsafe_allow_html=True)

def get_circle_progress_html(percent):
    circum = 439.8
    offset = circum * (1 - percent/100)
    return f"""
    <div style="display: flex; justify-content: flex-end; align-items: center;">
        <div style="position: relative; width: 130px; height: 130px; border-radius: 50%; background: #E0E5EC; box-shadow: 9px 9px 16px #bec3c9, -9px -9px 16px #ffffff; display: flex; align-items: center; justify-content: center;">
            <svg width="130" height="130"><circle stroke="#d1d9e6" stroke-width="10" fill="transparent" r="55" cx="65" cy="65"/><circle stroke="#FF0000" stroke-width="10" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" stroke-linecap="round" fill="transparent" r="55" cx="65" cy="65" style="transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;"/></svg>
            <div style="position: absolute; font-size: 26px; font-weight: 900;">{percent}%</div>
        </div>
    </div>
    """

def init_session_state():
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB", "event_date": "(2026 FEB)",
        "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], "scope_of_word": [],
        "messages": [{"role": "assistant", "content": "Firebean Brain Online. Ready to Turn Policy into Play."}], 
        "project_photos": [], "hero_index": 0, "processed_photos": {},
        "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": []
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

# --- 4. Main App ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session_state()
    apply_styles()

    # 進度計算 (11 維度)
    filled = sum([1 for f in ["client_name", "project_name", "venue", "challenge", "solution"] if st.session_state[f]])
    filled += (1 if st.session_state.who_we_help else 0) + (1 if st.session_state.what_we_do else 0) + (1 if st.session_state.scope_of_word else 0)
    filled += (1 if st.session_state.logo_white and st.session_state.logo_black else 0) 
    filled += (1 if st.session_state.project_photos else 0) + (1 if st.session_state.ai_content else 0)
    percent = int((filled / 11) * 100)

    # Header
    c1, c2 = st.columns([1, 1])
    with c1: st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=180)
    with c2: st.markdown(get_circle_progress_html(percent), unsafe_allow_html=True)

    t1, t2 = st.tabs(["💬 Collector", "📋 Review & Sync"])

    with t1:
        # Logo 區
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("🎨 Client Branding (PNG Only)")
        lc1, lc2 = st.columns(2)
        with lc1:
            ub = st.file_uploader("Black Logo", type=['png'], key="logo_b")
            if ub and st.button("📏 Standardize Black"): st.session_state.logo_black = standardize_logo(ub)
        with lc2:
            uw = st.file_uploader("White Logo", type=['png'], key="logo_w")
            if uw and st.button("📏 Standardize White"): st.session_state.logo_white = standardize_logo(uw)
        st.markdown('</div>', unsafe_allow_html=True)

        # Info 區 (包含 What we do / SOW)
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.subheader("📝 Project Information")
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

        # Chatbot
        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("🤖 Firebean Chatbot")
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.write(m["content"])
            if p := st.chat_input("詢問項目細節..."):
                st.session_state.messages.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                result = call_gemini_rest(f"Context SOW: {st.session_state.scope_of_word}\nUser Inquiry: {p}")
                if result:
                    reply = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "AI Timeout.")
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.subheader("📸 Manna Gallery (Outpainting)")
            files = st.file_uploader("Upload 8 Photos", accept_multiple_files=True)
            if files:
                st.session_state.project_photos = files
                hero_choice = st.radio("🌟 Hero Banner?", [f"P{i+1}" for i in range(len(files))], horizontal=True)
                st.session_state.hero_index = int(hero_choice[1:]) - 1
                cols = st.columns(4)
                for i, f in enumerate(files):
                    with cols[i%4]:
                        is_proc = i in st.session_state.processed_photos
                        if is_proc: st.markdown('<div class="ai-status-tag">✨ AI READY</div>', unsafe_allow_html=True)
                        if st.button(f"🪄 AI P{i+1}", key=f"ai_{i}"):
                            st.session_state.processed_photos[i] = manna_ai_enhance(f)
                            st.rerun()
                        
                        # 預覽修正方向
                        img_src = st.session_state.processed_photos.get(i, ImageOps.exif_transpose(Image.open(f)))
                        border = "hero-border" if i == st.session_state.hero_index else ""
                        st.markdown(f'<div class="{border}">', unsafe_allow_html=True)
                        st.image(img_src, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.session_state.challenge = st.text_area("Challenge (EN)", st.session_state.challenge)
        st.session_state.solution = st.text_area("Solution (EN)", st.session_state.solution)
        if st.button("🪄 生成五路文案"):
            res = call_gemini_rest(f"Project: {st.session_state.project_name}\nChallenge: {st.session_state.challenge}\nGenerate JSON: slide_en, linkedin_en, facebook_tc, ig_threads_oral, web_en, web_tc, web_jp.")
            if res:
                text = res.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "")
                st.session_state.ai_content = json.loads(text[text.find('{'):text.rfind('}')+1])
                st.success("文案生成成功！")
        if st.session_state.ai_content: st.json(st.session_state.ai_content)
        if st.button("🚀 Confirm & Sync"):
            b64s = []
            for i, f in enumerate(st.session_state.project_photos):
                img = st.session_state.processed_photos.get(i, ImageOps.exif_transpose(Image.open(f)))
                buf = io.BytesIO(); img.convert("RGB").save(buf, format="JPEG", quality=85)
                b64s.append(base64.b64encode(buf.getvalue()).decode())
            payload = {
                "client_name": st.session_state.client_name, "project_name": st.session_state.project_name, 
                "scope_of_work": ", ".join(st.session_state.scope_of_word), "ai": st.session_state.ai_content, "images": b64s,
                "logo_white": st.session_state.logo_white, "logo_black": st.session_state.logo_black
            }
            res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=45)
            if "Success" in res.text: st.balloons(); st.success("Master DB 同步成功！")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 5. 永久除錯終端 (Firebean Debug Terminal) ---
    st.markdown("---")
    with st.expander("🛠️ Firebean Brain Debug Terminal", expanded=True):
        if not st.session_state.debug_logs:
            st.write("Terminal Stand-by...")
        else:
            for l in reversed(st.session_state.debug_logs):
                cls = f"debug-{l['type']}"
                st.markdown(f"<div class='debug-terminal {cls}'>[{l['time']}] {l['msg']}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
