import json
import re
from llm import get_model
from prompts import SKILL_EXTRACTION_PROMPT

def extract_pr_skills(pr_data):
    client = get_model()
    
    full_prompt = SKILL_EXTRACTION_PROMPT.format(
        title=pr_data.get('title', 'N/A'),
        description=pr_data.get('description', 'N/A'),
        diff=pr_data.get('diff', '')
    )
    
    # Modern SDK syntax: client.models.generate_content
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite-preview', # Or 'gemini-1.5-flash'
        contents=full_prompt
    )
    
    # Extract text from response
    raw_text = response.text
    
    # Robust JSON extraction
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(raw_text)
    except Exception as e:
        print(f"Error: Could not parse LLM output as JSON. Raw text: {raw_text}")
        return {"required_skills": [], "summary": "Extraction failed"}