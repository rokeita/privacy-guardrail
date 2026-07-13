import streamlit as st
import re
from google import genai
from google.genai import errors
import time

# Set up page layout
st.set_page_config(page_title="AI Privacy Guardrail", layout="wide")

st.title("🛡️ AI Privacy Guardrail & Summarizer")
st.caption("Scan and redact PII locally before sending text to the Cloud AI.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Redaction Filters")
st.sidebar.markdown("Choose what sensitive data to block:")
filter_email = st.sidebar.checkbox("Emails", value=True)
filter_phone = st.sidebar.checkbox("Phone Numbers", value=True)
filter_card = st.sidebar.checkbox("Credit Cards", value=True)
filter_ghana = st.sidebar.checkbox("Ghana Cards", value=True)

# Dynamic Redaction Logic
def redact_text(text):
    if filter_email:
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
    if filter_phone:
        text = re.sub(r'\+?\d{1,4}[-.\s]?\d{1,10}[-.\s]?\d{1,10}', '[REDACTED_PHONE]', text)
    if filter_card:
        text = re.sub(r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b', '[REDACTED_CREDIT_CARD]', text)
    if filter_ghana:
        text = re.sub(r'GHA-\d{9}-\d', '[REDACTED_GHANA_CARD]', text)
    return text

# --- MAIN APP LAYOUT ---
user_input = st.text_area("Paste your raw customer intake notes / documents here:", height=150, 
                          placeholder="Type or paste something containing sensitive info...")

if st.button("Process Securely", use_container_width=True):
    if not user_input.strip():
        st.warning("Please enter some text first!")
    else:
        # Step 1: Local Redaction
        with st.spinner("Locally scanning and redacting sensitive data..."):
            time.sleep(0.5)
            safe_text = redact_text(user_input)
        
        # Display Redaction Results
        st.subheader("📋 Cleaned (Safe) Text")
        st.info(safe_text)
        
        # NEW feature: One-click download button
        st.download_button(
            label="📥 Download Cleared Text (.txt)",
            data=safe_text,
            file_name="sanitized_document.txt",
            mime="text/plain",
            use_container_width=True
        )
        
        st.write("---")
        
        # Step 2: Request Cloud AI Summary
        st.subheader("🤖 Gemini Executive Summary")
        
        api_key = st.secrets ["GEMINI_API_KEY"]
        
        with st.spinner("Sending safe text to Gemini..."):
            try:
                client = genai.Client(api_key=api_key)
                prompt = f"Write a short, professional executive summary based ONLY on this safe, redacted text:\n\n{safe_text}"
                
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=prompt,
                )
                
                if response.text:
                    st.success(response.text)
                else:
                    st.warning("Gemini returned an empty response.")
                    
            except errors.APIError as e:
                st.error(f"Gemini API Error: {e.message}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")