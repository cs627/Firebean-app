import streamlit as st
import google.generativeai as genai
import requests
import io
import base64
import time
import json
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from rembg import remove
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
Follow 'Bridge Structure' (Boring Challenge -> Creative Translation -> Data Result).
LinkedIn/Slides: EN only. IG/Threads: Canto-slang. Website: Trilingual.
"""

# --- 2. 核心功能：Logo 與 影像處理 ---
def process_manna_logo(logo_file):
    with st.spinner("🎨 Manna AI 正在進行 Logo 提煉 (Vector-Look)..."):
        input_image = Image.open(logo_file)
        no_bg = remove(input_image, alpha_matting=True)
        alpha = no_bg.getchannel('A').filter(ImageFilter.GaussianBlur(radius=0.5))
        alpha = alpha.point(lambda p: 255 if p > 128 else 0)
        
        white_logo = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
        white_logo.putalpha(alpha)
        black_logo = Image.new("RGBA", no_bg.size, (0, 0, 0, 255))
        black_logo.putalpha(alpha)

        def to_b64(img):
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode()
        return to_b64(white_logo), to_b64(black_logo)

def manna_ai_enhance(image_file):
    img = Image.open(image_file)
    w, h = img.size
    with st.spinner("🚀 Manna AI Cinematic 處理中..."):
        img = ImageEnhance.Contrast(img).enhance(1.35)
        if w < 1920:
            new_h = int(h * (1920 / w))
            img = img.resize((1920, new_h), Image.Resampling.LANCZOS)
    return img

def sync_data(url, payload):
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. UI 視覺樣式 (這是 Logs 報錯遺漏的部分) ---
def apply_styles():
    st.markdown("""
        <style>
        header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E0E5EC; color: #2D3436; font-family: 'Inter', sans-serif; }
        .neu-card { background: #E0E5EC; border-radius: 30px; box-shadow: 15px 15px 30px #bec3c9, -15px -15px 30px #ffffff;
