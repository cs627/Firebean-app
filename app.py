import streamlit as st
import google.generativeai as genai
import io
import base64
import json
import requests
from PIL import Image, ImageOps, ImageEnhance
from datetime import datetime

# --- 1. 核心配置 (鎖死同步連結與 API 池) ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwLR9MVr4rNgCQeXd2zGq43_F3ncsml_t7IP4OkjqBNtdNiv0ETitiuzx4oif3T0tCZ/exec"
API_KEYS_POOL = [
    "AIzaSyA-5qXWjtzlUWP0IDMVUByMXdbylt8rTSA",
    "AIzaSyCVuoSuWV3tfGCu2tjikCkMOVRWCBFne20",
    "AIzaSyCZKtjLqN4FUQ76c3DYoDW20tTkFki_Rxk"
]

# --- 2. 鎖死 Firebean PR DNA 系統指令 ---
FIREBEAN_SYSTEM_PROMPT = """
Identity: 'Institutional Cool'. Strategy: 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
Motto: 'Turn Policy into Play'.

INTERVIEW MODE (ACTIVE):
- 你是資深 PR Director。若 Challenge 或 Solution 資訊不足，必須以「反問」啟發用戶（例如提供場景猜測）。
- 在資料未圓滿補充前，嚴禁輸出 JSON。

OUTPUT SPEC:
- 語言：EN, Traditional Chinese (TC), Japanese (JP)。絕對禁止簡體中文。
- 字數：Challenge 與 Solution 每一段必須精簡在 50-100 字/words 內。
- 內容：必須自然植入 "Firebean PR" 關鍵字。
"""

# --- 3. 核心功能函式 ---

def init_session():
    """確保 App 載入時變數完整，防止 Load 不到"""
    fields = {
        "client_name": "", "project_name": "", "venue": "", "event_year": "2026", "event_month": "FEB",
        "youtube_link": "", "challenge": "", "solution": "", "who_we_help": [], "what_we_do": [], 
        "scope_of_word": [], "messages": [{"role": "assistant", "content": "Firebean Director Online. 我睇到你入咗基本資料，但最關鍵嘅 Challenge 同 Solution 係咩？係咪 Topic 太悶難吸客？"}],
        "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": []
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def call_gemini_engine(prompt, is_json=False):
    """SDK 輪詢引擎：確保 Key 失效時自動切換"""
    for key in API_KEYS_POOL:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=FIREBEAN_SYSTEM_PROMPT)
            config = genai.types.GenerationConfig(response_mime_type="application/json" if is_json else "text/plain")
            response = model.generate_content(prompt, generation_config=config)
            if response and response.text: return response.text
        except: continue
    return None

def sync_to_master_db(ai_results):
    """鎖死原本 A-T 欄 Mapping 邏輯 """
    try:
        # 對接原本 GAS doPost 的變數名
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
            "ai_content": ai_results # 傳送完整 JSON 供 GAS 拆解 L-S 欄
        }
        res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=25)
        return res.status_code == 200
    except Exception as e:
        st.error(f"Sync Error: {str(e)}")
        return False

# --- 4. Main UI 邏輯 ---

def main():
    st.set_page_config(page_title="Firebean Brain 2026", layout="wide")
    init_session()
    
    # 這裡加入你原本的 apply_styles(), Logo 上傳, Info & SOW UI ...
    
    tab1, tab2 = st.tabs(["💬 AI Interviewer", "🚀 Sync to Master DB"])
    
    with tab1:
        st.subheader("🤖 Firebean Director 智能訪談 (反問引導模式)")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.write(m["content"])
            
        if p := st.chat_input("向 PR Director 匯報細節..."):
            st.session_state.messages.append({"role": "user", "content": p})
            # 發送對話歷史給 AI
            context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
            res_text = call_gemini_engine(f"History:\n{context}\nUser: {p}")
            
            # 判斷是回傳問題還是 JSON
            if "{" in res_text and "}" in res_text:
                try:
                    st.session_state.ai_content = json.loads(res_text[res_text.find("{"):res_text.rfind("}")+1])
                    st.success("✅ 訪談圓滿！六路文案已生成 (精簡 50-100 字)。")
                except: st.error("JSON 解析出錯")
            else:
                st.session_state.messages.append({"role": "assistant", "content": res_text})
                st.rerun()

    with tab2:
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("🚀 Confirm & Sync to Master Ecosystem"):
                if sync_to_master_db(st.session_state.ai_content):
                    st.balloons()
                    st.success("✅ 數據已成功同步至 Google Sheet A-T 欄。")
        else:
            st.warning("請先完成 AI 訪談以生成文案。")

if __name__ == "__main__":
    main()
