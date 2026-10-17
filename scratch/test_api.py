import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
from google import genai
from prompts import get_standard_prompt
from api import generate_quiz_content
import audio

load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
prompt = get_standard_prompt('Spelling', '2 - Medium', '')
resp = generate_quiz_content(client, prompt)
data = json.loads(resp.output_text)
print(f"Generated {len(data)} questions")
audio_tested = False
for q in data:
    word = q.get('target_word')
    q_type = q.get('type')
    q_text = q.get('question', '')[:50]
    print(f"Type: {q_type} | Target Word: {word!r} | Question: {q_text}...")
    if word and not audio_tested:
        b = audio.get_audio_bytes(word)
        print(f"Audio generated for {word!r}: {len(b)} bytes")
        audio_tested = True
