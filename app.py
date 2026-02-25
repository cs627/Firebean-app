import streamlit as st
import google.generativeai as genai
import json
import requests
from datetime import datetime

# --- 配置區：鎖定舊有打通的連結 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwLR9MVr4rNgCQeXd2zGq43_F3ncsml_t7IP4OkjqBNtdNiv0ETitiuzx4oif3T0tCZ/exec"

# --- 鎖死系統指令：Firebean PR DNA 與 訪談規則 ---
FIREBEAN_CORE_INSTRUCTION = """
Role: Firebean Senior PR Director.
Identity: 'Institutional Cool'. 
DNA: 'Turn Policy into Play' & 'Bridge Structure'.

INTERVIEW LOGIC (MUST FOLLOW):
1. Proactive Probing: 如果 Challenge/Solution 資料不足，必須用「反問」或「場景猜測」來引導同事。
2. 例子：如果同事答唔到 Challenge，你可以問：「係咪個 Topic 本身好悶難吸引大眾？定係因為場地限制令我哋要用科技解決？」
3. 嚴禁直接生成 JSON，直到資料達到圓滿標準。

GENERATION SPEC:
- 語言：嚴禁簡體中文。鎖定 EN, TC (繁體), JP。
- 長度：Challenge/Solution 每段嚴格控制在 50-100 字。
- 同步：輸出必須符合 6 路文案 JSON 結構。
"""

# --- 核心同步函數：對接 GAS A-T 欄 ---
def sync_to_master_db(ai_results):
    try:
        # 完全保留你原本的 doPost 結構邏輯，唔會整斷舊功能
        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "client_name": st.session_state.client_name,
            "project_name": st.session_state.project_name,
            "youtube_link": st.session_state.youtube_link,
            "challenge": ai_results['6_website']['tc']['content'],
            "solution": ai_results['6_website']['tc']['content'],
            "ai_content": ai_results # 這裡包含了 L-S 欄的所有多平台內容
        }
        res = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=30)
        return res.status_code == 200
    except Exception as e:
        st.error(f"Sync failed: {str(e)}")
        return False

# --- 智能訪談邏輯 ---
def call_firebean_ai(user_input):
    # 這裡會結合 FIREBEAN_CORE_INSTRUCTION 進行生成
    # 邏輯：判斷是回傳「追問文字」還是「最終 JSON」
    pass

# --- UI 介面 ---
# (此處為 Streamlit 主循環，整合訪談對話框與同步按鈕)
