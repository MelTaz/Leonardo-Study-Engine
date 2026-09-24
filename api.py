import streamlit as st

def generate_quiz_content(client, prompt: str):
    """
    Sends the generated prompt to Gemini and automatically falls back to a 
    supported alternative model if the primary server is experiencing high demand.
    """
    quiz_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "question_type": {"type": "string"},
                "question": {"type": "string"},
                "visual_code": {"type": "string"},
                "options": {"type": "array", "items": {"type": "string"}},
                "correct_answer": {"type": "string"},
                "explanation": {"type": "string"}
            },
            "required": ["type", "question", "options", "correct_answer", "explanation"]
        }
    }

    try:
        # Primary attempt
        interaction = client.interactions.create(
            model='gemini-3.8-flash',
            input=prompt,
            response_format=quiz_schema
        )
        return interaction
    except Exception as e:
        # Backup attempt using a modern supported model if a 503 Server Error occurs
        st.toast("⚠️ Server busy, using backup channel...", icon="🔄")
        interaction = client.interactions.create(
            model='gemini-3.5-flash-lite',
            input=prompt,
            response_format=quiz_schema
        )
        return interaction