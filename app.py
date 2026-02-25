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
# 這是你提供的正式 Google Apps Script 網址
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
LinkedIn/Slides: EN only (Hook-Shift-Proof). IG/Threads: Canto-slang (世一, Firm, Vibe). Website: Trilingual (EN, TC, JP).
"""

# --- 2. 核心功能：Logo 與 影像處理 ---
def process_manna_logo(logo_file):
    """將上傳的 Logo 去背景並生成黑、白兩色高對比版本"""
    with st.spinner("🎨 Manna AI 正在進行 Logo 提煉 (Vector-Look)..."):
        input_image = Image.open(logo_file)
        # AI 高級去背景
        no_bg = remove(input_image, alpha_matting=True)
        # 提取 Alpha 層並平滑化，產生向量感
        alpha = no_bg.getchannel('A').filter(ImageFilter.GaussianBlur(radius=0.5))
        alpha = alpha.point(lambda p: 255 if p > 128 else 0)
        
        # 生成透明底純白 Logo (適合深色 Slide)
        white_logo = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
        white_logo.putalpha(alpha)
        
        # 生成透明底純黑 Logo (適合白色 Website)
        black_logo = Image.new("RGBA", no_bg.size, (
