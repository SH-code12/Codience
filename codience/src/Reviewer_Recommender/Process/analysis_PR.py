import json
import os
import re
import concurrent.futures
from codience.src.Reviewer_Recommender.Process.llm import generate_with_resilience
from codience.src.Reviewer_Recommender.Process.prompts import SKILL_EXTRACTION_PROMPT, FILE_DIFF_SUMMARY_PROMPT

PR_SUMMARY_WORKERS = int(os.getenv("PR_SUMMARY_WORKERS", "3"))

def summarize_file_diff(file_data):
    try:
        prompt = FILE_DIFF_SUMMARY_PROMPT.format(
            filename=file_data['filename'],
            patch=file_data['patch']
        )
        result = generate_with_resilience(prompt, purpose="pr_file_summary")
        if not result.get("ok"):
            return ""
        return f"File: {file_data['filename']}\nSummary: {result.get('text', '').strip()}\n"
    except Exception as e:
        print(f"⚠️ Failed to summarize file {file_data.get('filename')}: {e}")
        return ""

def extract_pr_skills(pr_data):
    files = pr_data.get('files', [])
    aggregated_summaries = ""
    
    if files:
        print(f"🚀 Summarizing {len(files)} files in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=PR_SUMMARY_WORKERS) as executor:
            summaries = list(executor.map(summarize_file_diff, files))
            aggregated_summaries = "\n".join(summaries)
    else:
        aggregated_summaries = "No code files changed or diffs available."
    
    full_prompt = SKILL_EXTRACTION_PROMPT.format(
        title=pr_data.get('title', 'N/A'),
        description=pr_data.get('description', 'N/A'),
        diff=aggregated_summaries
    )
    
    result = generate_with_resilience(full_prompt, purpose="pr_skill_extraction")
    if not result.get("ok"):
        return {"required_skills": [], "summary": "Extraction failed", "detected_languages": []}
    raw_text = result.get("text", "")
    
    # Robust JSON extraction
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(raw_text)
    except Exception as e:
        print(f"Error: Could not parse LLM output as JSON. Raw text: {raw_text}")
        return {"required_skills": [], "summary": "Extraction failed", "detected_languages": []}