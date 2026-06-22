import os
from google import genai
from dotenv import load_dotenv

load_dotenv()


def get_model():
    """Return a Gemini client. Mirrors the Reviewer Recommender so both
    AI features share the same provider and GEMINI_API_KEY."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return client
