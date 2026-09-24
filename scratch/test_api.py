import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

try:
    interaction = client.interactions.create(
        model='gemini-3.8-flash',
        input="Generate 2 questions in JSON format."
    )
    print("OUTPUT TEXT:")
    print(repr(interaction.output_text))
    print("STEPS:")
    for step in interaction.steps:
        print(step)
except Exception as e:
    print(f"Error: {e}")

