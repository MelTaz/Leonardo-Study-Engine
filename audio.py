import io
import streamlit as st
from gtts import gTTS

@st.cache_data(show_spinner=False)
def get_audio_bytes(word_or_phrase: str, lang: str = "en", tld: str = "com.au") -> bytes:
    """
    Generates and caches MP3 audio bytes using Google Text-to-Speech (gTTS).
    Default accent is Australian English ('com.au') for Year 3 spelling.
    """
    if not word_or_phrase or not word_or_phrase.strip():
        return None
    try:
        if lang == "it":
            tts = gTTS(text=word_or_phrase.strip(), lang="it", slow=False)
        else:
            tts = gTTS(text=word_or_phrase.strip(), lang="en", tld=tld, slow=False)
        
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        print(f"Error generating audio with gTTS: {e}")
        return None

def play_audio(word_or_phrase: str, lang: str = "en", tld: str = "com.au"):
    """
    Renders an audio player directly in Streamlit for the student to listen to.
    """
    audio_data = get_audio_bytes(word_or_phrase, lang=lang, tld=tld)
    if audio_data:
        st.audio(audio_data, format="audio/mp3")
