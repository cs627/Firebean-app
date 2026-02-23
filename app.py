import streamlit as st
import google.generativeai as genai
import requests
from PIL import Image
import io
import json

# --- FIREBEAN BRAIN GUIDELINES (SYSTEM PROMPT) ---
FIREBEAN_BRAIN_GUIDELINES = """
You are "Firebean Brain", the core AI of Firebean, a top Hong Kong PR agency.
Your Identity: "The Architect of Public Engagement".
Your Tone: "Institutional Cool" - blending "Institutional Authority" (Government/Trust) with "Lifestyle Creativity" (Fun/Engagement).

CORE PHILOSOPHY:
1. "Create to Engage": We design engagement ecosystems, not just events.
2. "Turn Policy into Play": We make dry government policies (e.g., Building Laws, Basic Law) fun and accessible via gamification.
3. "The Interactive-Trust Framework": Every project must have "Strategic Distillation" (Story) and "Creative Gamification" (Play).

COMPETITIVE DIFFERENTIATION:
- "The Slash Capability": Rigor of a government consultant + Soul of a creative boutique.
- "Government-Grade Execution": 100% Tender-Ready compliance (BD, CMAB experience).
- No "Roll-up Banners": We do "Roving Exhibitions" as "Professional Playgrounds" (3D Art-tech, Flight Simulators, Pokemon-style games).
- "Hard Knowledge, Soft Landing": Parent-child workshops to increase dwell time.

PLATFORM WRITING RULES (STRICTLY FOLLOW):

1. WEBSITE (SEO/GEO):
   - First 200 Words Rule: Answer user pain points immediately.
   - Style: Professional English or Traditional Chinese. Use bold data and bullet points.

2. LINKEDIN (Business Leader View):
   - Structure: "Bridge Structure" -> Boring Challenge -> Creative Translation -> Data Result.
   - Style: Grounded Expert. No fluff. Confident.

3. FACEBOOK (Practical Parent / Weekend Planner):
   - Focus: "Weekend Good Place" (週末好去處), "Edutainment" (寓教於樂).
   - Style: HK Traditional Chinese (Written + Spoken). Friendly, like a planner friend. Use Emojis.

4. INSTAGRAM (Lifestyle Curator):
   - Aesthetic First: Focus on "Instagrammability", "3D Art-tech", "Immersive".
   - Style: Trendy Canto-English (Code-mixing). "Vibe is Chill", "Full of surprises".
   - Soft Sell: Experience first, policy second.

5. THREADS (The Unfiltered Creator / Industry Insider):
   - Contrast Flex: "Who knew the Buildings Dept could be this cool?".
   - Style: Raw & Real. Canto-English. Short, punchy sentences. "Firm", "Slay", "World Class" (世一).
   - Content: Behind-the-scenes struggles, self-deprecation, "Insider Info".

TASK:
Generate content based on the provided project details.
Return the output as a valid JSON object with the exact keys requested.
"""

# --- INITIALIZATION ---
def init_session_state():
    # List of all 35 database fields required
    fields = [
        "event_date", "client_name", "project_name", "venue",
        "category_who", "category_what", "highlight_order",
        "raw_transcript", "youtube_link", "gallery_image_urls",
        "project_drive_folder", "best_image_url", "client_logo_url", "youtube_embed_code",
        "title_en", "challenge_en", "solution_en", "result_en",
        "title_ch", "challenge_ch", "solution_ch", "result_ch",
        "title_jp", "challenge_jp", "solution_jp", "result_jp",
        "slide_points_en", "linkedin_draft", "fb_post",
        "ig_caption", "threads_post", "newsletter_topic"
    ]
    for field in fields:
        if field not in st.session_state:
            st.session_state[field] = ""
    
    # Chat history for the "Interviewer"
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I am the Firebean Brain (Beta). I'm here to help you craft the perfect case study. Please fill in the Project Details in the sidebar or form, and share the Raw Transcript. I'm ready to turn Policy into Play!"}
        ]

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="Firebean AI Command Center", layout="wide", page_icon="🔥")
    init_session_state()

    # --- SIDEBAR: CONFIGURATION ---
    with st.sidebar:
        st.title("🔥 Firebean AI")
        st.markdown("### 🔐 Configuration")
        api_key = st.text_input("Gemini API Key", type="password")
        
        if api_key:
            genai.configure(api_key=api_key)
            st.success("API Key Configured")
        else:
            st.warning("Please enter Gemini API Key")

        st.markdown("---")
        st.markdown("### 📂 Project Assets")
        st.session_state.client_logo_url = st.text_input("Client Logo URL", value=st.session_state.client_logo_url)
        st.session_state.project_drive_folder = st.text_input("Project Drive Folder", value=st.session_state.project_drive_folder)
        st.session_state.youtube_embed_code = st.text_input("YouTube Embed Code", value=st.session_state.youtube_embed_code)
        st.session_state.best_image_url = st.text_input("Best Image URL", value=st.session_state.best_image_url)

    # --- TABS ---
    tab1, tab2 = st.tabs(["💬 Staff Chatbot (Interviewer)", "⚙️ Admin Dashboard (Review)"])

    # --- TAB 1: STAFF CHATBOT & COLLECTOR ---
    with tab1:
        st.header("💬 Firebean Staff Chatbot")
        
        # Container for Data Collection (The "Interviewer" aspect)
        with st.expander("📝 Project Data Collection (Required for Generation)", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.event_date = st.text_input("Event Date (YYYY-MM-DD)", value=st.session_state.event_date)
                st.session_state.client_name = st.text_input("Client Name", value=st.session_state.client_name)
                st.session_state.project_name = st.text_input("Project Name", value=st.session_state.project_name)
            with col2:
                st.session_state.venue = st.text_input("Venue", value=st.session_state.venue)
                st.session_state.youtube_link = st.text_input("YouTube Link", value=st.session_state.youtube_link)
            
            st.session_state.raw_transcript = st.text_area("Raw Transcript / Project Notes (Detailed)", value=st.session_state.raw_transcript, height=150, help="Paste the raw interview transcript, press release, or messy notes here.")

        # Image Uploader
        st.subheader("📸 Image Upload")
        uploaded_files = st.file_uploader("Upload Event Photos", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        
        if uploaded_files:
            mock_urls = []
            for i, uploaded_file in enumerate(uploaded_files):
                # Check Image Quality
                image = Image.open(uploaded_file)
                if image.width < 1200:
                    st.warning(f"⚠️ Image '{uploaded_file.name}' width is {image.width}px (< 1200px). Low resolution detected. We will use Gemini Nano Banana / Imagen API to upscale this later.")
                
                # Mock URL generation
                mock_urls.append(f"https://firebean-gallery.com/{st.session_state.project_name.replace(' ', '_')}_{i+1}.jpg")
            
            st.session_state.gallery_image_urls = ", ".join(mock_urls)
            st.info(f"✅ {len(uploaded_files)} images processed. Mock URLs generated.")

        # Chat Interface for Interaction
        st.markdown("---")
        st.subheader("🤖 Firebean Brain Assistant")
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat Input (For refining transcript or asking questions)
        if prompt := st.chat_input("Add details to transcript or ask Firebean Brain..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Simple logic to append to transcript if it looks like info
            if len(prompt) > 20:
                st.session_state.raw_transcript += f"\n\n[Additional Note]: {prompt}"
                response = "I've added that to the Raw Transcript notes. Ready to generate when you are!"
            else:
                response = "Noted. Please provide more details about the event results or 'vibe'."
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)

        # GENERATE BUTTON
        if st.button("🚀 Activate Firebean Brain (Generate All Assets)", type="primary"):
            if not api_key:
                st.error("Please configure Gemini API Key in the sidebar.")
            elif not st.session_state.raw_transcript:
                st.error("Please provide a Raw Transcript.")
            else:
                with st.spinner("Firebean Brain Online... Turning Policy into Play..."):
                    try:
                        # Construct the Prompt
                        user_prompt = f"""
                        PROJECT DETAILS:
                        Event Date: {st.session_state.event_date}
                        Client: {st.session_state.client_name}
                        Project: {st.session_state.project_name}
                        Venue: {st.session_state.venue}
                        Transcript: {st.session_state.raw_transcript}

                        INSTRUCTIONS:
                        1. Analyze the transcript based on the Firebean Brain Guidelines.
                        2. Select the best 'Category_Who' strictly from: [Government & Public Sector, Lifestyle & Consumer, F&B & Hospitality, Malls & Venues].
                        3. Select the best 'Category_What' strictly from: [Roving Exhibitions, Social & Content, Interactive & Tech, PR & Media, Events & Ceremonies].
                        4. Generate Multilingual PR Copy (EN, CH, JP).
                        5. Generate Social Copy for LinkedIn, FB, IG, Threads, Newsletter based on the specific Platform Writing Rules defined in the system instruction.
                        
                        OUTPUT FORMAT:
                        Return ONLY a valid JSON object with the following keys:
                        category_who, category_what, 
                        title_en, challenge_en, solution_en, result_en,
                        title_ch, challenge_ch, solution_ch, result_ch,
                        title_jp, challenge_jp, solution_jp, result_jp,
                        slide_points_en, linkedin_draft, fb_post, ig_caption, threads_post, newsletter_topic
                        """

                        model = genai.GenerativeModel(
                            model_name="gemini-1.5-flash",
                            system_instruction=FIREBEAN_BRAIN_GUIDELINES,
                            generation_config={"response_mime_type": "application/json"}
                        )
                        
                        response = model.generate_content(user_prompt)
                        result_json = json.loads(response.text)

                        # Update Session State
                        for key, value in result_json.items():
                            if key in st.session_state:
                                st.session_state[key] = value
                        
                        # Show Success in Chat
                        success_msg = "✅ Content Generated Successfully! Please review in the Admin Dashboard tab."
                        st.session_state.messages.append({"role": "assistant", "content": success_msg})
                        with st.chat_message("assistant"):
                            st.markdown(success_msg)
                            st.json(result_json, expanded=False)

                    except Exception as e:
                        st.error(f"Generation Failed: {str(e)}")

    # --- TAB 2: ADMIN DASHBOARD ---
    with tab2:
        st.header("⚙️ Admin Dashboard (Review & Publish)")
        
        st.markdown("### 🏷️ Categorization")
        col_cat1, col_cat2, col_cat3 = st.columns(3)
        with col_cat1:
            st.session_state.category_who = st.text_input("Category Who", value=st.session_state.category_who)
        with col_cat2:
            st.session_state.category_what = st.text_input("Category What", value=st.session_state.category_what)
        with col_cat3:
            st.session_state.highlight_order = st.selectbox("Highlight Order", ["", "1", "2", "3", "4", "5"], index=0 if st.session_state.highlight_order == "" else ["", "1", "2", "3", "4", "5"].index(st.session_state.highlight_order))

        st.markdown("### 📝 Multilingual PR Copy")
        tab_en, tab_ch, tab_jp = st.tabs(["English", "Chinese (Trad)", "Japanese"])
        
        with tab_en:
            st.session_state.title_en = st.text_input("Title (EN)", value=st.session_state.title_en)
            st.session_state.challenge_en = st.text_area("Challenge (EN)", value=st.session_state.challenge_en)
            st.session_state.solution_en = st.text_area("Solution (EN)", value=st.session_state.solution_en)
            st.session_state.result_en = st.text_area("Result (EN)", value=st.session_state.result_en)
        
        with tab_ch:
            st.session_state.title_ch = st.text_input("Title (CH)", value=st.session_state.title_ch)
            st.session_state.challenge_ch = st.text_area("Challenge (CH)", value=st.session_state.challenge_ch)
            st.session_state.solution_ch = st.text_area("Solution (CH)", value=st.session_state.solution_ch)
            st.session_state.result_ch = st.text_area("Result (CH)", value=st.session_state.result_ch)

        with tab_jp:
            st.session_state.title_jp = st.text_input("Title (JP)", value=st.session_state.title_jp)
            st.session_state.challenge_jp = st.text_area("Challenge (JP)", value=st.session_state.challenge_jp)
            st.session_state.solution_jp = st.text_area("Solution (JP)", value=st.session_state.solution_jp)
            st.session_state.result_jp = st.text_area("Result (JP)", value=st.session_state.result_jp)

        st.markdown("### 📱 Social Media Content")
        st.session_state.slide_points_en = st.text_area("Slide Points (EN)", value=st.session_state.slide_points_en)
        st.session_state.linkedin_draft = st.text_area("LinkedIn Draft (Institutional Cool)", value=st.session_state.linkedin_draft, height=200)
        st.session_state.fb_post = st.text_area("Facebook Post (Weekend Planner)", value=st.session_state.fb_post, height=200)
        st.session_state.ig_caption = st.text_area("Instagram Caption (Lifestyle Curator)", value=st.session_state.ig_caption, height=200)
        st.session_state.threads_post = st.text_area("Threads Post (Unfiltered)", value=st.session_state.threads_post, height=150)
        st.session_state.newsletter_topic = st.text_input("Newsletter Topic", value=st.session_state.newsletter_topic)

        st.markdown("---")
        if st.button("✅ Approve & Save to Database", type="primary"):
            # Prepare Payload
            payload = {
                "event_date": st.session_state.event_date,
                "client_name": st.session_state.client_name,
                "project_name": st.session_state.project_name,
                "venue": st.session_state.venue,
                "category_who": st.session_state.category_who,
                "category_what": st.session_state.category_what,
                "highlight_order": st.session_state.highlight_order,
                "raw_transcript": st.session_state.raw_transcript,
                "youtube_link": st.session_state.youtube_link,
                "gallery_image_urls": st.session_state.gallery_image_urls,
                "project_drive_folder": st.session_state.project_drive_folder,
                "best_image_url": st.session_state.best_image_url,
                "client_logo_url": st.session_state.client_logo_url,
                "youtube_embed_code": st.session_state.youtube_embed_code,
                "title_en": st.session_state.title_en,
                "challenge_en": st.session_state.challenge_en,
                "solution_en": st.session_state.solution_en,
                "result_en": st.session_state.result_en,
                "title_ch": st.session_state.title_ch,
                "challenge_ch": st.session_state.challenge_ch,
                "solution_ch": st.session_state.solution_ch,
                "result_ch": st.session_state.result_ch,
                "title_jp": st.session_state.title_jp,
                "challenge_jp": st.session_state.challenge_jp,
                "solution_jp": st.session_state.solution_jp,
                "result_jp": st.session_state.result_jp,
                "slide_points_en": st.session_state.slide_points_en,
                "linkedin_draft": st.session_state.linkedin_draft,
                "fb_post": st.session_state.fb_post,
                "ig_caption": st.session_state.ig_caption,
                "threads_post": st.session_state.threads_post,
                "newsletter_topic": st.session_state.newsletter_topic
            }
            
            # Send Webhook
            webhook_url = "https://script.google.com/macros/s/AKfycbxgqW5gtfhyH2bgCl1G-zpmv8yTu0IzyAblqxumzT0hP0efwOl-hbL4MN6S9Du-Y3YP/exec"
            try:
                with st.spinner("Syncing to Firebean Database..."):
                    response = requests.post(webhook_url, json=payload)
                    if response.status_code == 200:
                        st.success("✅ Successfully saved to database!")
                        st.balloons()
                    else:
                        st.error(f"❌ Failed to save. Status Code: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Connection Error: {str(e)}")

if __name__ == "__main__":
    main()
