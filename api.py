import streamlit as st
from google.genai import types

def generate_quiz_content(client, prompt: str):
    """
    Sends the generated prompt to Gemini and automatically falls back to a 
    supported alternative model if the primary server is experiencing high demand.
    """
    try:
        # Primary attempt
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        return response
    except Exception as e:
        # Backup attempt using a modern supported model if a 503 Server Error occurs
        st.toast("⚠️ Server busy, using backup channel...", icon="🔄")
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        return response