import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageDraw, ImageOps 
from datetime import datetime

# --- 1. 核心配置 (保持原有端點) ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- NEW: 系統自動生成邏輯 (ID 與 日期) ---
def generate_system_metadata():
    """自動生成大寫無符號 Project_id 與標準化 Sort_date"""
    # 1. 映射月份為數字 (Sort_date 用)
    month_map = {m: str(i+1).zfill(2) for i, m in enumerate(MONTH_OPTIONS)}
    m_num = month_map.get(st.session_state.event_month, "01")
    sort_date = f"{st.session_state.event_year}-{m_num}-01"

    # 2. 獲取當前行數生成 ID (向 Sheet 索取當前總行數)
    try:
        # 這裡會觸發 Google Sheet Script 的 doGet 
        count_res = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=5)
        next_index = int(count_res.text) + 1 if count_res.status_code == 200 else 100
    except:
        next_index = 999 
    
    # 格式：FB + 年份 + 三位序號 (如 FB2026005)
    project_id = f"FB{st.session_state.event_year}{str(next_index).zfill(3)}"
    
    return project_id, sort_date

# --- 2. 系統 Prompt (完整保留) ---
FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Lead PR Strategist, and an expert Chief Editor and B2B/B2C Journalist for a premium online magazine.
Task: Transform diagnostic data into a professional PR strategy JSON. 
... (中間內容省略以節省篇幅，請保留你原始 app (9).py 內的完整文字) ...
"""

# --- 3. 核心功能函數 (與原本完全一致) ---
def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key: return None
    try:
        genai.configure(api_key=secret_key)
        model = genai.GenerativeModel(model_name=STABLE_MODEL_ID, system_instruction=FIREBEAN_SYSTEM_PROMPT)
        contents = [prompt]
        if image_files:
            for f in image_files:
                if hasattr(f, "seek"): f.seek(0)
                img = Image.open(f)
                img = ImageOps.exif_transpose(img)
                img.thumbnail((800, 800))
                contents.append(img)
        response = model.generate_content(contents, generation_config={"response_mime_type": "application/json" if is_json else "text/plain","temperature": 0.2})
        if response and response.text:
            text = response.text.strip()
            if not is_json: return text
            match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
            return match.group(0) if match else text
    except Exception as e:
        st.error(f"❌ AI 錯誤: {e}")
    return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector", "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": str(CURRENT_YEAR), "event_month": "FEB", "category": WHO_WE_HELP_OPTIONS[0],
        "what_we_do": [], "scope": [], "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", "challenge": "", "solution": "", "hero_photo_index": 0
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()

    # --- 自定義 CSS (與原本一致) ---
    st.markdown("""<style>...</style>""", unsafe_allow_html=True)

    # --- 頂部導覽列 ---
    tabs = ["Project Collector", "Expert Questions", "Review & Multi-Sync"]
    cols = st.columns(len(tabs))
    for i, tab in enumerate(tabs):
        if cols[i].button(tab, use_container_width=True, type="primary" if st.session_state.active_tab == tab else "secondary"):
            st.session_state.active_tab = tab

    # --- TAB 1: Project Collector ---
    if st.session_state.active_tab == "Project Collector":
        # ... (保留你 app (9).py 中關於輸入欄位的完整代碼)
        pass

    # --- TAB 2: Expert Questions ---
    if st.session_state.active_tab == "Expert Questions":
        # ... (保留你 app (9).py 中關於 AI 診斷問題的完整代碼)
        pass

    # --- TAB 3: Review & Multi-Sync (核心修改處) ---
    if st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        
        # 按鈕：生成文案
        if st.button("生成六大平台對接文案", use_container_width=True):
            # ... (執行 AI 生成邏輯)
            pass

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            
            # 按鈕：同步至雲端
            if st.button("Confirm & Sync (Sheet + Slide + Drive)", type="primary", use_container_width=True):
                with st.spinner("🔄 正在運算系統編號與同步數據..."):
                    try:
                        # 1. 核心：生成 Project_id 與 Sort_date
                        project_id, sort_date = generate_system_metadata()
                        
                        # 2. 核心：圖片處理 (保持 Hero 優先排序)
                        processed_imgs = []
                        for f in st.session_state.project_photos:
                            if hasattr(f, "seek"): f.seek(0)
                            img = Image.open(f).convert("RGB")
                            img = ImageOps.exif_transpose(img) # 自動校正轉向
                            img.thumbnail((1600, 1600))
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG", quality=85)
                            processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

                        h_idx = st.session_state.hero_photo_index
                        if processed_imgs and h_idx < len(processed_imgs):
                            hero = processed_imgs.pop(h_idx)
                            processed_imgs.insert(0, hero)

                        # 3. 核心：封裝 Payload (包含新增的 Z 與 AA 欄位)
                        payload = {
                            "action": "sync_project",
                            "Project_id": project_id,      # 新增 Z 欄
                            "Sort_date": sort_date,        # 新增 AA 欄
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
                            "logo_white": st.session_state.logo_white, 
                            "logo_black": st.session_state.logo_black,
                            "images": processed_imgs, 
                            "ai_content": st.session_state.ai_content
                        }
                        
                        # 4. 核心：雙向同步
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=90)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=90)
                        
                        log_debug(f"Sync: {project_id} | Sheet({r1.status_code}) Slide({r2.status_code})", "success")
                        st.balloons()
                        st.success(f"✅ 同步對位成功！編號：{project_id}")
                    except Exception as e:
                        st.error(f"同步失敗: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
