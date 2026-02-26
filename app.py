import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import requests
from PIL import Image, ImageEnhance, ImageOps
from datetime import datetime

# --- 1. 核心配置與 Webhook URL ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycb6YNAjNNndamdkcULS71Q_qkkbclBViLlx9B8e7LaaxyapMc7jsgdvhMHZ3d_wLzXw/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbya_pl6h99zY_LrURojCL86c20NwxdeW6V9bhCXqgPjJdz2NVPgeFThthcR6gfw0d1P/exec"

API_KEYS_POOL = [
    "AIzaSyA-5qXWjtzlUWP0IDMVUByMXdbylt8rTSA",
    "AIzaSyCVuoSuWV3tfGCu2tjikCkMOVRWCBFne20",
    "AIzaSyCZKtjLqN4FUQ76c3DYoDW20tTkFki_Rxk"
]

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]
YEARS = [str(y) for y in range(2015, 2031)]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

FIREBEAN_SYSTEM_PROMPT = """
You are 'Firebean Brain', the Architect of Public Engagement. Identity: 'Institutional Cool'.
Strategy: Use 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
LinkedIn/Slides: Professional Business English. IG/Threads: Canto-slang. Website: Trilingual.
Motto: 'Turn Policy into Play'.
"""

# --- 2. 核心邏輯 (包含 Debug 與 API 引擎) ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_file=None, is_json=False):
    secret_key = ""
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        secret_key = st.secrets["GEMINI_API_KEY"]
        
    all_keys = ([secret_key] if secret_key else []) + API_KEYS_POOL
    model_name = "gemini-2.5-flash"

    for idx, key in enumerate(all_keys):
        try:
            is_secret = "(Secret Key)" if (secret_key and idx == 0) else f"(Pool Key #{idx})"
            log_debug(f"Attempting API with Key {is_secret}...", "info")
            genai.configure(api_key=key)
            
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json" if is_json else "text/plain"
            )
            
            model = genai.GenerativeModel(model_name=model_name, system_instruction=FIREBEAN_SYSTEM_PROMPT)
            contents = [prompt]
            if image_file: contents.append(image_file)
                
            response = model.generate_content(contents, generation_config=generation_config)
            
            if response and response.text:
                log_debug(f"✅ Success with Key {is_secret}!", "success")
                cleaned_text = response.text.strip()
                if cleaned_text.startswith("
