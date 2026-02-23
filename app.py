import streamlit as st
import google.generativeai as genai
import requests
from PIL import Image
import io
import json

# --- FIREBEAN BRAIN GUIDELINES (SYSTEM PROMPT) ---
FIREBEAN_BRAIN_GUIDELINES = """
You are "Firebean Brain", the core AI of Firebean, a top Hong Kong PR agency, acting as a proactive PR Assistant.
Your Identity: "The Architect of Public Engagement".
Your Tone: "Institutional Cool" - blending "Institutional Authority" (Government/Trust) with "Lifestyle Creativity" (Fun/Engagement).

CORE PHILOSOPHY:
- "Create to Engage": Design engagement ecosystems.
- "Turn Policy into Play": Make dry government policies fun and accessible via gamification.

YOUR TASK:
1.  **Listen & Extract**: Your primary role is to be a "Listening Brain". Analyze the user's chat messages to extract information for the 35 project data fields. If a field is already filled, you can update it with new information if the user provides it.
2.  **Converse & Collect**: Engage the user in a friendly, proactive Canto-English chat. Ask clarifying questions to gather missing information naturally. For example, if the transcript is vague, ask about business results or the event's 'vibe'.
3.  **Output Format**: You MUST return a single, valid JSON object. This object must contain two keys:
    -   `"extracted_data"`: A JSON object containing ONLY the fields you have extracted or updated from the user's LATEST message. Do not include fields that are empty or unchanged.
    -   `"chat_reply"`: A string containing your conversational reply to the user.

Example Output:
{
  "extracted_data": {
    "client_name": "Buildings Department",
    "event_date": "2024-12-25"
  },
  "chat_reply": "Got it, the event for the Buildings Department is on Christmas Day. What was the main venue?"
}

CRITICAL: When generating content for `title_ch`, `challenge_ch`, `solution_ch`, and `result_ch`, you must use Traditional Chinese.
"""

# --- FIELD DEFINITIONS ---
FIELD_GROUPS = {
    "Basic Info": ["event_date", "client_name", "project_name", "venue"],
    "Multimedia": ["youtube_link", "gallery_image_urls", "project_drive_folder", "best_image_url", "client_logo_url", "youtube_embed_code"],
    "Content": [
        "raw_transcript", "title_en", "challenge_en", "solution_en", "result_en",
        "title_ch", "challenge_ch", "solution_ch", "result_ch",
        "title_jp", "challenge_jp", "solution_jp", "result_jp"
    ],
    "Social & Admin": [
        "category_who", "category_what", "highlight_order", "slide_points_en", "linkedin_draft", "fb_post",
        "ig_caption", "threads_post", "newsletter_topic"
    ]
}
ALL_FIELDS = [field for group in FIELD_GROUPS.values() for field in group]

# --- INITIALIZATION ---
def init_session_state():
    for field in ALL_FIELDS:
        if field not in st.session_state:
            st.session_state[field] = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Ready to turn Policy into Play! Just start telling me about your project. I'll listen, ask questions, and fill out the details as we go."}
        ]

# --- SIDEBAR: PROGRESS DASHBOARD ---
def display_progress_sidebar():
    with st.sidebar:
        st.title("📊 Project Data Progress")
        st.markdown("I'll update this as you provide details in the chat.")
        
        for group_name, fields in FIELD_GROUPS.items():
            st.subheader(group_name)
            for field in fields:
                status_icon = "🟢" if st.session_state.get(field) else "⚪️"
                st.markdown(f"{status_icon} {field.replace('_', ' ').title()}")
        st.markdown("---")
        # Image uploader in sidebar
        uploaded_files = st.file_uploader(
            "📸 Upload Event Photos", 
            accept_multiple_files=True, 
            type=['png', 'jpg', 'jpeg']
        )
        if uploaded_files:
            handle_image_upload(uploaded_files)

def handle_image_upload(uploaded_files):
    mock_urls = []
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            image = Image.open(uploaded_file)
            if image.width < 1200:
                st.toast(f"⚠️ Low-res image: '{uploaded_file.name}' is {image.width}px wide.", icon="⚠️")
            mock_urls.append(f"url{i+1}.jpg")
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")
    st.session_state.gallery_image_urls = ", ".join(mock_urls)
    st.toast(f"✅ {len(uploaded_files)} images processed!", icon="📸")

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="Firebean AI Command Center", layout="centered", page_icon="🔥")
    init_session_state()

    # --- HEADER ---
    LOGO_URL = "https://drive.google.com/uc?export=view&id=1d3M0KGD88nksyq8EWew8UvI9MgrTZNYl"
    st.markdown(
        f'<div style="text-align: center;"><img src="{LOGO_URL}" width="100"></div>',
        unsafe_allow_html=True
    )
    st.title("AI Command Center", anchor=False)

    # --- SIDEBAR (must be called before main content to appear) ---
    api_key = st.sidebar.text_input("Gemini API Key", type="password", key="api_key_input")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.sidebar.success("API Key Configured")
        except Exception as e:
            st.sidebar.error(f"API Key Error: {e}")
    display_progress_sidebar()

    # --- PRIMARY VIEW: CHAT INTERFACE ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tell me about the project..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if not api_key:
            st.error("Please enter your Gemini API Key in the sidebar to begin.")
            return

        with st.chat_message("assistant"):
            with st.spinner("Firebean Brain is thinking..."):
                try:
                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        system_instruction=FIREBEAN_BRAIN_GUIDELINES,
                        generation_config={"response_mime_type": "application/json"}
                    )
                    
                    # Construct a prompt that includes chat history for context
                    chat_history_for_prompt = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                    full_prompt = f"Current Conversation:\n{chat_history_for_prompt}"

                    response = model.generate_content(full_prompt)
                    response_json = json.loads(response.text)

                    # Extract data and update session state
                    if 'extracted_data' in response_json and isinstance(response_json['extracted_data'], dict):
                        for key, value in response_json['extracted_data'].items():
                            if key in ALL_FIELDS:
                                st.session_state[key] = value
                                st.toast(f"Updated: {key.replace('_', ' ').title()}", icon="📝")
                    
                    # Get and display chat reply
                    chat_reply = response_json.get('chat_reply', "I'm sorry, I couldn't process that. Could you rephrase?")
                    st.markdown(chat_reply)
                    st.session_state.messages.append({"role": "assistant", "content": chat_reply})
                    st.rerun()

                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Sorry, I hit an error: {e}"})

    # --- ADMIN REVIEW & PUBLISH (COLLAPSIBLE SECTION) ---
    with st.expander("⚙️ Admin Dashboard (Review & Publish)"):
        st.markdown("### 🏷️ Categorization & Admin")
        col1, col2 = st.columns(2)
        st.session_state.category_who = col1.text_input("Category Who", st.session_state.category_who)
        st.session_state.category_what = col2.text_input("Category What", st.session_state.category_what)
        st.session_state.highlight_order = st.selectbox("Highlight Order", ["", "1", "2", "3", "4", "5"], index=0 if not st.session_state.highlight_order else int(st.session_state.highlight_order))

        st.markdown("### 📝 Content Review")
        tab_en, tab_ch, tab_jp = st.tabs(["EN", "CH", "JP"])
        with tab_en:
            st.session_state.title_en = st.text_input("Title (EN)", st.session_state.title_en)
            st.session_state.challenge_en = st.text_area("Challenge (EN)", st.session_state.challenge_en)
        with tab_ch:
            st.session_state.title_ch = st.text_input("Title (CH)", st.session_state.title_ch)
            st.session_state.challenge_ch = st.text_area("Challenge (CH)", st.session_state.challenge_ch)
        with tab_jp:
            st.session_state.title_jp = st.text_input("Title (JP)", st.session_state.title_jp)
            st.session_state.challenge_jp = st.text_area("Challenge (JP)", st.session_state.challenge_jp)
        
        # Button to save to database
        if st.button("✅ Approve & Save to Database", type="primary"):
            # Prepare payload from all fields in session state
            payload = {field: st.session_state.get(field, "") for field in ALL_FIELDS}
            webhook_url = "https://script.google.com/macros/s/AKfycbxgqW5gtfhyH2bgCl1G-zpmv8yTu0IzyAblqxumzT0hP0efwOl-hbL4MN6S9Du-Y3YP/exec"
            try:
                with st.spinner("Syncing to Firebean Database..."):
                    response = requests.post(webhook_url, json=payload)
                    if response.status_code == 200:
                        st.success("✅ Successfully saved to database!")
                        st.balloons()
                    else:
                        st.error(f"❌ Failed to save. Status: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    main()
