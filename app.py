import streamlit as st
import google.generativeai as genai
import requests
import json
import io
from PIL import Image
from rembg import remove

# --- 1. 系統核心設定 ---
FIREBEAN_BRAIN_GUIDELINES = """
You are "Firebean Brain", a top HK PR agency AI. 
Tone: "Institutional Cool". Generate PR content and Slide Scripts in JSON format.
"""

# --- 2. 初始化欄位 ---
def init_session_state():
    fields = [
        "event_date", "client_name", "project_name", "venue", "raw_transcript",
        "title_en", "challenge_en", "solution_en", "result_en",
        "title_ch", "challenge_ch", "solution_ch", "result_ch",
        "linkedin_draft", "fb_post", "ig_caption", "threads_post",
        "slide_1_cover", "slide_2_challenge", "slide_3_solution", "slide_4_results"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Dickson! Logo Studio now supports Black & White icons. Let's make your project assets shine!"}]

# --- 3. UI 樣式 ---
def apply_custom_style():
    st.markdown("""
        <style>
        .stApp { background-color: #e0e5ec; }
        .neu-card { background-color: #e0e5ec; border-radius: 15px; box-shadow: 8px 8px 16px #b8bec5, -8px -8px 16px #ffffff; padding: 20px; margin-bottom: 20px; }
        .stButton>button { border-radius: 12px; box-shadow: 5px 5px 10px #b8bec5, -5px -5px 10px #ffffff; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. 主程式 ---
def main():
    st.set_page_config(page_title="Firebean AI Command Center", layout="wide", page_icon="🔥")
    apply_custom_style()
    init_session_state()

    # Logo & Title
    logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
    st.image(logo_url, width=280)
    
    with st.sidebar:
        st.header("🔐 Config")
        api_key = st.text_input("Gemini API Key", value="AIzaSyDupK7JjQAjcR5P5f9eqyev5uYRe4ZOKdI", type="password")
        if api_key: genai.configure(api_key=api_key)
        
        st.markdown("---")
        st.subheader("📊 Sync Assets")
        st.session_state.youtube_link = st.text_input("YouTube URL", st.session_state.youtube_link)

    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat & Input", "🎨 Logo Studio", "⚙️ Admin Review", "🗂️ Slide Script"])

    # TAB 1: 對話與資料擷取
    with tab1:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Input event details..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.raw_transcript += f"\n{prompt}"
            with st.chat_message("user"): st.markdown(prompt)
        
        if st.button("🚀 Activate Firebean Brain", type="primary"):
            with st.spinner("Processing..."):
                try:
                    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=FIREBEAN_BRAIN_GUIDELINES)
                    response = model.generate_content(st.session_state.raw_transcript, generation_config={"response_mime_type": "application/json"})
                    res_data = json.loads(response.text)
                    for k, v in res_data.items():
                        if k in st.session_state: st.session_state[k] = v
                    st.success("Assets Generated!")
                except Exception as e: st.error(f"Error: {e}")

    # TAB 2: Logo Studio (新增顏色選擇)
    with tab2:
        st.header("🎨 AI Logo Studio")
        st.info("去背並生成高清透明標誌。")
        
        col_ctrl1, col_ctrl2 = st.columns([2, 1])
        with col_ctrl1:
            logo_file = st.file_uploader("Upload source photo/logo", type=['png', 'jpg', 'jpeg'])
        with col_ctrl2:
            icon_color = st.radio("Select Icon Color", ["Black (純黑)", "White (純白)"])

        if logo_file:
            col_in, col_out = st.columns(2)
            input_image = Image.open(logo_file)
            col_in.image(input_image, caption="Original Photo", use_column_width=True)
            
            if st.button("🪄 Convert to Transparent Icon"):
                with st.spinner("Processing image..."):
                    # 1. 使用 rembg 去背
                    output_image = remove(input_image)
                    
                    # 2. 獲取 Alpha Channel (透明度層)
                    alpha = output_image.getchannel('A')
                    
                    # 3. 根據選擇設定顏色
                    if "Black" in icon_color:
                        fill_rgb = (0, 0, 0, 255) # 純黑
                        preview_bg = "#ffffff" # 預覽用白色背景
                    else:
                        fill_rgb = (255, 255, 255, 255) # 純白
                        preview_bg = "#333333" # 預覽用深灰色背景以便看清白色標誌
                    
                    # 4. 重新著色
                    color_layer = Image.new('RGBA', output_image.size, fill_rgb)
                    final_icon = Image.composite(color_layer, Image.new('RGBA', output_image.size, (0,0,0,0)), alpha)
                    
                    # 5. 顯示結果 (加上背景色以便預覽)
                    st.markdown(f'<div style="background-color:{preview_bg}; padding:10px; border-radius:10px; text-align:center;">', unsafe_allow_html=True)
                    col_out.image(final_icon, caption=f"Processed {icon_color} Icon", use_column_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # 6. 下載
                    buf = io.BytesIO()
                    final_icon.save(buf, format="PNG")
                    st.download_button(
                        label=f"📥 Download {icon_color} PNG", 
                        data=buf.getvalue(), 
                        file_name=f"Firebean_Icon_{icon_color.split()[0]}.png", 
                        mime="image/png"
                    )

    # TAB 3 & 4 (保持原樣)
    with tab3:
        st.header("⚙️ Admin Dashboard")
        st.session_state.client_name = st.text_input("Client", st.session_state.client_name)
        if st.button("✅ Save to Google Sheet"):
            st.success("Saved!")

    with tab4:
        st.header("🗂️ Slide Script")
        st.write(f"**Slide 1:** {st.session_state.slide_1_cover}")
        st.write(f"**Slide 2:** {st.session_state.slide_2_challenge}")

if __name__ == "__main__":
    main()
