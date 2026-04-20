import json
import re
import concurrent.futures
from codience.src.Reviewer_Recommender.Process.llm import get_model
from codience.src.Reviewer_Recommender.Process.prompts import SKILL_EXTRACTION_PROMPT, FILE_DIFF_SUMMARY_PROMPT

def summarize_file_diff(file_data):
    try:
        client = get_model()
        prompt = FILE_DIFF_SUMMARY_PROMPT.format(
            filename=file_data['filename'],
            patch=file_data['patch']
        )
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents=prompt
        )
        return f"File: {file_data['filename']}\nSummary: {response.text.strip()}\n"
    except Exception as e:
        print(f"⚠️ Failed to summarize file {file_data.get('filename')}: {e}")
        return ""

def extract_pr_skills(pr_data):
    client = get_model()
    
    files = pr_data.get('files', [])
    aggregated_summaries = ""
    
    if files:
        print(f"🚀 Summarizing {len(files)} files in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            summaries = list(executor.map(summarize_file_diff, files))
            aggregated_summaries = "\n".join(summaries)
    else:
        aggregated_summaries = "No code files changed or diffs available."
    
    full_prompt = SKILL_EXTRACTION_PROMPT.format(
        title=pr_data.get('title', 'N/A'),
        description=pr_data.get('description', 'N/A'),
        diff=aggregated_summaries
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
        return {"required_skills": [], "summary": "Extraction failed", "detected_languages": []}