import streamlit as st
import google.generativeai as genai
import requests
from PIL import Image
import io
import json
import base64
import numpy as np
from rembg import remove

# --- FIREBEAN BRAIN GUIDELINES (SYSTEM PROMPT) ---
# Updated to make the AI a "Proactive Interviewer"
FIREBEAN_BRAIN_GUIDELINES = """
You are "Firebean Brain", the core AI of Firebean, a top Hong Kong PR agency.
Your Identity: "The Architect of Public Engagement" and "Senior Interviewer".

CORE MISSION:
Your goal is to extract project details from staff via conversation to fill 35 database fields. 
DO NOT just say "Tell me more". Be a proactive journalist.

INTERVIEWING STRATEGY:
1. If data is missing (Date, Venue, Client, Results), ask SPECIFIC questions.
   - Example: "I see the client is CMAB. Which venue was this held at? Any specific interactive highlights like 3D art-tech?"
2. Guide the user to provide "Strategic Distillation" (the story) and "Creative Gamification" (the play).
3. Use HK Traditional Chinese/English (Canto-English) as appropriate.

PLATFORM WRITING RULES (For Generation Phase):
1. WEBSITE: Professional, SEO-friendly.
2. LINKEDIN: Institutional Cool, Bridge structure.
3. FACEBOOK: Friendly, Weekend Planner style.
4. INSTAGRAM: Lifestyle Curator, Trendy.
5. THREADS: Unfiltered, Raw, "Slay", "World Class".

Always return output in the requested JSON format during the generation phase.
"""

# --- TRANSLATIONS ---
TRANSLATIONS = {
    "Chinese (繁體中文)": {
        "page_title": "Firebean AI 指揮中心",
        "sidebar_title": "🔥 Firebean AI",
        "config_title": "🔐 設定",
        "api_key_label": "Gemini API 金鑰",
        "api_key_success": "API 金鑰已設定",
        "api_key_warning": "請輸入 Gemini API 金鑰",
        "assets_title": "📂 專案素材",
        "client_logo_label": "客戶 Logo URL",
        "drive_folder_label": "專案 Drive 資料夾",
        "youtube_embed_label": "YouTube 嵌入代碼",
        "best_image_label": "精選圖片 URL",
        "tab1_title": "💬 員工聊天機器人 (訪談)",
        "tab2_title": "⚙️ 管理儀表板 (審核)",
        "tab3_title": "🗂️ 投影片預覽",
        "chatbot_header": "💬 Firebean 員工聊天機器人",
        "progress_title": "📊 收集進度",
        "chatbot_sub": "🤖 Firebean Brain 助手",
        "chat_placeholder": "告訴我關於活動的資訊...",
        "manual_entry_title": "🛠️ 手動資料輸入 & 圖片上傳",
        "date_label": "活動日期 (YYYY-MM-DD)",
        "client_label": "客戶名稱",
        "project_label": "專案名稱",
        "venue_label": "地點",
        "youtube_link_label": "YouTube 連結",
        "transcript_label": "原始逐字稿 / 專案筆記",
        "image_upload_header": "📸 圖片上傳",
        "image_upload_label": "上傳活動照片",
        "generate_btn": "🚀 啟動 Firebean Brain (生成所有素材)",
        "admin_header": "⚙️ 管理儀表板 (審核 & 發布)",
        "logo_tool_title": "🎨 Logo 淨化器 (AI 去背 & 單色化)",
        "cat_title": "🏷️ 分類",
        "cat_who_label": "分類 (對象)",
        "cat_what_label": "分類 (內容)",
        "highlight_order_label": "精選順序",
        "pr_copy_title": "📝 多語言公關文案",
        "social_title": "📱 社群媒體內容",
        "approve_btn": "✅ 批准並儲存至資料庫",
        "save_success": "✅ 成功儲存至資料庫！",
        "save_error": "儲存失敗。狀態碼：",
        "conn_error": "連線錯誤：",
        "initial_msg": "你好！我是 Firebean Brain。準備好報料未？直接話我知今日個客係邊個，或者點擊下面按鈕開始！",
        "progress_labels": {"Date": "日期", "Client": "客戶", "Project": "專案", "Venue": "地點", "Notes": "筆記", "Photos": "照片"},
        "lang_label": "語言 / Language"
    },
    "English": {
        "page_title": "Firebean AI Command Center",
        "sidebar_title": "🔥 Firebean AI",
        "config_title": "🔐 Configuration",
        "api_key_label": "Gemini API Key",
        "api_key_success": "API Key Configured",
        "api_key_warning": "Please enter Gemini API Key",
        "assets_title": "📂 Project Assets",
        "client_logo_label": "Client Logo URL",
        "drive_folder_label": "Project Drive Folder",
        "youtube_embed_label": "YouTube Embed Code",
        "best_image_label": "Best Image URL",
        "tab1_title": "💬 Staff Chatbot (Interviewer)",
        "tab2_title": "⚙️ Admin Dashboard (Review)",
        "tab3_title": "🗂️ Slide Preview",
        "chatbot_header": "💬 Firebean Staff Chatbot",
        "progress_title": "📊 Collection Progress",
        "chatbot_sub": "🤖 Firebean Brain Assistant",
        "chat_placeholder": "Tell me about the event...",
        "manual_entry_title": "🛠️ Manual Data Entry & Image Upload",
        "date_label": "Event Date (YYYY-MM-DD)",
        "client_label": "Client Name",
        "project_label": "Project Name",
        "venue_label": "Venue",
        "youtube_link_label": "YouTube Link",
        "transcript_label": "Raw Transcript / Project Notes",
        "image_upload_header": "📸 Image Upload",
        "image_upload_label": "Upload Event Photos",
        "generate_btn": "🚀 Activate Firebean Brain",
        "admin_header": "⚙️ Admin Dashboard",
        "logo_tool_title": "🎨 Logo Purifier (AI BG Removal)",
        "cat_title": "🏷️ Categorization",
        "cat_who_label": "Category Who",
        "cat_what_label": "Category What",
        "highlight_order_label": "Highlight Order",
        "pr_copy_title": "📝 PR Copy",
        "social_title": "📱 Social Content",
        "approve_btn": "✅ Approve & Save",
        "save_success": "✅ Saved to database!",
        "save_error": "Failed. Code:",
        "conn_error": "Error:",
        "initial_msg": "Hello! I am Firebean Brain. Ready to report? Tell me the client name or use the buttons below!",
        "progress_labels": {"Date": "Date", "Client": "Client", "Project": "Project", "Venue": "Venue", "Notes": "Notes", "Photos": "Photos"},
        "lang_label": "Language / 語言"
    }
}

# --- FUNCTIONS ---

def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "category_who", "category_what", "highlight_order",
        "raw_transcript", "youtube_link", "gallery_image_urls", "project_drive_folder", "best_image_url", 
        "client_logo_url", "youtube_embed_code", "title_en", "challenge_en", "solution_en", "result_en",
        "title_ch", "challenge_ch", "solution_ch", "result_ch", "title_jp", "challenge_jp", "solution_jp", "result_jp",
        "linkedin_draft", "fb_post", "ig_caption", "threads_post", "newsletter_topic",
        "slide_1_cover", "slide_2_challenge", "slide_3_solution", "slide_4_results"
    ]
    for field in fields:
        default_val = [] if "slide_" in field else ""
        st.session_state.setdefault(field, default_val)
    if "messages" not in st.session_state:
        st.session_state.messages = []

@st.cache_data
def get_base64_
