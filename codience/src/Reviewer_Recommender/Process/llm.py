import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_model():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return client