import streamlit as st
import google.generativeai as genai
import requests
import json
import io
import base64
from PIL import Image
from rembg import remove

# --- 1. 核心性格與「奪命追問」策略 ---
SYSTEM_INSTRUCTION = """
你係 Firebean Brain，香港最頂尖嘅 PR 策略大腦。
【性格】高明、可愛、把口好甜但要求好嚴格。
【任務】你要幫老細執靚份 Success Case Slide。
【追問規則】
你必須確保收齊以下 5 樣嘢。如果 user 未講，你要主動「反問」佢：
1. Client Name (邊個客？)
2. Project Name (個名夠唔夠 Firm？)
3. Venue (喺邊度搞？)
4. Challenge (遇到咩痛點？)
5. Solution (你點幫佢解決？)

每次回覆只問一個重點，唔好一次過問晒。
語氣要帶有 Vibe、Firm 同 Chill，常用 Emoji: ✨, 🥺, 💡, 📸。
"""

# --- 2. 初始化狀態 ---
def init_session_state():
    fields = ["event_date", "client_name", "project_name", "venue", "category", "scope", "challenge", "solution", "logo_b64"]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    # 第一句由 AI 開始
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "老細✨！終於返嚟喇！今日個 Project 搞成點？有冇咩場地或者痛點要我幫手 Vibe 吓佢？🥺"}]

# --- 3. UI 視覺強化 ---
def apply_neu_theme():
    # 計算能量槽進度
    track_fields = ["client_name", "project_name", "venue", "challenge", "solution"]
    filled = sum(1 for f in track_fields if st.session_state[f])
    progress_percent = int((filled / len(track_fields)) * 100)

    st.markdown(f"""
        <style>
        header {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        .stApp {{ background-color: #E0E5EC; color: #2D3436; }}

        /* Energy Bar */
        .energy-container {{ width: 100%; background: #E0E5EC; padding: 10px 0; position: sticky; top: 0; z-index: 999; }}
        .energy-bar-bg {{ height: 12px; background: #E0E5EC; border-radius: 10px; box-shadow: inset 4px 4px 8px #bec3c9, inset -4px -4px 8px #ffffff; overflow: hidden; margin: 0 20px; }}
        .energy-bar-fill {{ height: 100%; width: {progress_percent}%; background: linear-gradient(90deg, #FF4B4B, #FF8080); box-shadow: 0 0 15px #
