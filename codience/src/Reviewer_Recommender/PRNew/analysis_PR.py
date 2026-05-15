import json
import os
import re
import concurrent.futures
from typing import Dict, Any, List
import sys
sys.path.insert(0, '/home/shahd/Desktop/Grduation/codience/src/Reviewer_Recommender/PRNew')

from .llm import generate_with_resilience
from .prompts import (
    SKILL_EXTRACTION_PROMPT, 
    FILE_DIFF_SUMMARY_PROMPT,
    SENIORITY_SIGNALS_PROMPT
)

PR_SUMMARY_WORKERS = int(os.getenv("PR_SUMMARY_WORKERS", "3"))

def summarize_file_diff(file_data: Dict) -> str:
    """Summarize a single file diff using LLM."""
    try:
        prompt = FILE_DIFF_SUMMARY_PROMPT.format(
            filename=file_data.get('filename', 'unknown'),
            patch=file_data.get('patch', 'No patch available')
        )
        result = generate_with_resilience(prompt, purpose="pr_file_summary")
        if not result.get("ok"):
            return ""
        return f"File: {file_data['filename']}\nSummary: {result.get('text', '').strip()}\n"
    except Exception as e:
        print(f"⚠️ Failed to summarize file {file_data.get('filename')}: {e}")
        return ""

def extract_seniority_signals(pr_data: Dict) -> List[str]:
    """Extract seniority signals (security, migration, performance) from PR."""
    full_text = f"Title: {pr_data.get('title', '')}\nDescription: {pr_data.get('description', '')}\n"
    
    # Also include diff snippets for signal detection
    files = pr_data.get('files', [])
    diff_snippets = []
    for f in files[:5]:  # Limit to first 5 files to avoid token bloat
        patch = f.get('patch', '')[:500]  # First 500 chars
        if patch:
            diff_snippets.append(patch)
    full_text += "\n".join(diff_snippets[:3])
    
    prompt = SENIORITY_SIGNALS_PROMPT.format(pr_text=full_text[:3000])
    result = generate_with_resilience(prompt, purpose="pr_skill_extraction")
    
    if result.get("ok"):
        try:
            json_match = re.search(r'\{.*\}', result.get("text", ""), re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("seniority_signals", [])
        except:
            pass
    return []

def extract_pr_skills(pr_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract skills, languages, and seniority signals from a Pull Request.
    
    Enhanced version with:
    - Better JSON parsing
    - Seniority signal extraction
    - Improved error handling
    """
    files = pr_data.get('files', [])
    aggregated_summaries = ""
    
    if files:
        print(f"🚀 Summarizing {len(files)} files in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=PR_SUMMARY_WORKERS) as executor:
            summaries = list(executor.map(summarize_file_diff, files))
            aggregated_summaries = "\n".join(s for s in summaries if s)
    else:
        aggregated_summaries = "No code files changed or diffs available."
    
    full_prompt = SKILL_EXTRACTION_PROMPT.format(
        title=pr_data.get('title', 'N/A'),
        description=pr_data.get('description', 'N/A'),
        diff=aggregated_summaries[:8000]  # Limit context size
    )
    
    result = generate_with_resilience(full_prompt, purpose="pr_skill_extraction")
    
    default_result = {
        "required_skills": [], 
        "summary": "Extraction failed", 
        "detected_languages": [],
        "rag_query": "",
        "seniority_signals": []
    }
    
    if not result.get("ok"):
        print(f"⚠️ Skill extraction failed: {result.get('reason')}")
        return default_result
    
    raw_text = result.get("text", "")
    
    # Robust JSON extraction with multiple strategies
    try:
        # Strategy 1: Find JSON object
        json_match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}', raw_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            # Strategy 2: Try parsing entire response
            parsed = json.loads(raw_text)
        
        # Ensure required fields exist
        result_dict = {
            "required_skills": parsed.get("required_skills", []),
            "detected_languages": parsed.get("detected_languages", []),
            "rag_query": parsed.get("rag_query", ""),
            "summary": parsed.get("summary", "PR analysis complete"),
            "seniority_signals": parsed.get("seniority_signals", [])
        }
        
        # If rag_query is empty, build a sensible default
        if not result_dict["rag_query"] and (result_dict["required_skills"] or result_dict["detected_languages"]):
            skills = result_dict["required_skills"][:3]
            langs = result_dict["detected_languages"][:2]
            result_dict["rag_query"] = f"A developer with expertise in {', '.join(skills + langs)}."
        
        # Try to extract additional seniority signals
        if not result_dict["seniority_signals"]:
            result_dict["seniority_signals"] = extract_seniority_signals(pr_data)
        
        return result_dict
        
    except Exception as e:
        print(f"Error parsing LLM output as JSON: {e}")
        print(f"Raw text: {raw_text[:500]}")
        return default_result