import os
import sys
import json
import requests
from pathlib import Path

# Add project root to python path to import internal modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

from codience.src.Reviewer_Recommender.PRNew.commit_history_utils import fetch_commit_history_for_author, save_checkpoint

load_dotenv()

# --- CONFIGURATION ---
TARGET_OWNER = "huggingface"
TARGET_REPO = "transformers"
COMMITS_TO_ANALYZE = 3  # Reduced for low-RAM speed
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:1b"

# List of developers you want to extract skills for
DEVELOPERS_TO_PROFILE = [
    "ArthurZucker", 
    "younesbelkada", 
    # Add more usernames here...
]

def extract_skills_with_ollama(commit_history) -> set:
    """
    Takes a developer's commit history and sends it to local Llama3 
    to extract rich architectural skills.
    """
    if not commit_history:
        return set()

    print(f"   🧠 Compiling diffs for {len(commit_history)} commits...")
    
    # Combine commit messages and diffs into a prompt
    combined_text = ""
    for commit in commit_history:
        msg = commit.get("commit", {}).get("message", "")
        files = commit.get("files", [])
        
        diff_summaries = []
        for f in files:
            filename = f.get("filename", "")
            patch = f.get("patch", "")[:300] # Take first 300 chars of diff to save context
            if patch:
                diff_summaries.append(f"File: {filename}\nDiff: {patch}")
                
        combined_text += f"\nCommit Message: {msg}\nChanges:\n" + "\n".join(diff_summaries) + "\n---\n"
    
    prompt = f"""
You are an expert Senior Software Architect analyzing a developer's commit history.
Based on the following commit messages and code diffs, extract the high-level technical skills, 
frameworks, and architectural patterns this developer is proficient in.

Focus on rich skills like "Dependency Injection", "State Management", "Concurrency", "React Hooks", "PyTorch Optimization", "CI/CD", etc.
DO NOT return generic terms like "bug fixing" or "coding".

Commit History:
{combined_text[:6000]} # Limit to 6000 chars

Return ONLY a valid JSON list of strings representing the skills. Example: ["React", "State Management", "Authentication"]
"""

    print(f"   🤖 Sending to Local Ollama ({OLLAMA_MODEL})...")
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json" # Forces Ollama to return JSON
        }, timeout=300) # Increased timeout to 5 minutes for slow hardware
        
        if response.status_code == 200:
            result_json = response.json()
            raw_text = result_json.get("response", "[]")
            skills = set(json.loads(raw_text))
            return skills
        else:
            print(f"   ❌ Ollama Error: {response.status_code} - {response.text}")
            return set()
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Failed to connect to Ollama at {OLLAMA_URL}. Is it running?")
        return set()
    except json.JSONDecodeError:
        print(f"   ❌ Failed to parse Ollama output as JSON.")
        return set()
    except Exception as e:
        print(f"   ❌ Error calling Local LLM: {e}")
        return set()

def run_batch_extraction():
    print("🚀 Starting Batch Skill Extraction via Local LLM...")
    
    for author in DEVELOPERS_TO_PROFILE:
        print(f"\n👨‍💻 Processing developer: {author}")
        
        # 1. Fetch their commit history from GitHub
        print("   📡 Fetching commits from GitHub API...")
        commits = fetch_commit_history_for_author(author, TARGET_OWNER, TARGET_REPO, limit=COMMITS_TO_ANALYZE)
        
        if not commits:
            print(f"   ⚠️ No commits found for {author}.")
            continue
            
        # 2. Extract deep skills using local LLM
        skills = extract_skills_with_ollama(commits)
        
        if skills:
            print(f"   ✅ Extracted {len(skills)} skills: {', '.join(skills)}")
            # 3. Save directly to your existing cache
            repo_key = f"{TARGET_OWNER}/{TARGET_REPO}"
            save_checkpoint(author, skills, repo_key)
        else:
            print(f"   ⚠️ No skills extracted for {author}.")

if __name__ == "__main__":
    run_batch_extraction()
