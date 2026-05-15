import os
import time
import requests
import json
import re
import concurrent.futures
from collections import defaultdict
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Set, Any 

# Add paths to Python path
sys.path.insert(0, '/home/shahd/Desktop/Grduation')
sys.path.insert(0, '/home/shahd/Desktop/Grduation/codience/src/Reviewer_Recommender/PRNew')

# Imports
from llm import generate_with_resilience, print_rate_limiter_stats
from prompts import FILE_DIFF_SUMMARY_PROMPT, COMMIT_CHUNK_SUMMARY_PROMPT, DEVELOPER_PROFILE_REDUCE_PROMPT
from profile_cache import ProfileCache

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
BASE_URL = "https://api.github.com"

session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https", HTTPAdapter(max_retries=retries))

# Initialize persistent cache
_profile_cache = ProfileCache()
CHECKPOINT_FILE = "/tmp/commit_skills_checkpoint.json"

def fetch_commits(owner, repo, limit=300):
    url = f"{BASE_URL}/repos/{owner}/{repo}/commits"
    try:
        target = max(1, int(limit))
        collected = []
        page = 1

        while len(collected) < target:
            batch_size = min(100, target - len(collected))
            r = session.get(
                url,
                headers=HEADERS,
                params={"per_page": batch_size, "page": page},
                timeout=15,
            )
            if r.status_code != 200:
                break

            batch = r.json() or []
            if not isinstance(batch, list) or not batch:
                break

            collected.extend(batch)
            if len(batch) < batch_size:
                break
            page += 1

        return collected[:target]
    except:
        return []

# REMOVED: LLM_BUDGET limit - let it run until complete
# No artificial budget - just let rate limiting handle it
llm_calls_made = 0  # Just for tracking, not limiting
SUMMARY_WORKERS = int(os.getenv("SUMMARY_WORKERS", "2"))

def call_llm(prompt, retries=3):
    """Call LLM without artificial budget limit"""
    global llm_calls_made
    llm_calls_made += 1
    
    result = generate_with_resilience(prompt, purpose="history_summary", max_retries=retries)
    if result.get("ok"):
        return result.get("text", "")
    
    # If LLM fails, return empty string (will retry via rate limiter)
    print(f"⚠️ LLM call failed after {result.get('attempts', 0)} attempts")
    return ""

def summarize_file_patch(file_data):
    if not file_data.get("patch"): return ""
    prompt = FILE_DIFF_SUMMARY_PROMPT.format(
        filename=file_data['filename'],
        patch=file_data['patch']
    )
    res = call_llm(prompt)
    if not res:
        return ""
    return f"File: {file_data['filename']}\nSummary: {res}"

def summarize_commit(commit_message, files):
    valid_files = [f for f in files if "patch" in f and not f["filename"].endswith(".csv") and not f["filename"].endswith("lock.json") and not f["filename"].endswith("poetry.lock")]
    
    file_summaries = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=SUMMARY_WORKERS) as executor:
        results = executor.map(summarize_file_patch, valid_files)
        for r in results:
            if r: file_summaries.append(r)
            
    if not file_summaries:
        return ""
        
    prompt = COMMIT_CHUNK_SUMMARY_PROMPT.format(
        commit_message=commit_message,
        file_summaries="\n\n".join(file_summaries)
    )
    return call_llm(prompt)

def save_checkpoint(author: str, skills: set, repo: str = "huggingface/transformers"):
    """Save progress to both cache and checkpoint file"""
    try:
        # Don't save empty profiles
        if not skills:
            print(f"⚠️ Skipping cache for {author} - no skills extracted")
            return False
        
        from collections import Counter
        skill_profile = Counter({skill.lower(): 1.0 for skill in skills})
        decay_tag = _profile_cache.decay_tag(2.0, 180)
        _profile_cache.set_profile(repo, author, skill_profile, decay_tag)
        
        # Save to checkpoint file
        checkpoint = load_checkpoint()
        checkpoint[author] = list(skills)
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        print(f"💾 Checkpoint saved: {author} ({len(skills)} skills)")
        return True
    except Exception as e:
        print(f"⚠️ Failed to save checkpoint for {author}: {e}")
        return False

def load_checkpoint():
    """Load previously saved checkpoint"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def load_from_cache(author: str, repo: str = "huggingface/transformers"):
    """Try to load skills from cache first"""
    try:
        decay_tag = _profile_cache.decay_tag(2.0, 180)
        profile = _profile_cache.get_profile(repo, author, decay_tag)
        if profile and len(profile) > 0:  # Only return non-empty profiles
            skills = [skill for skill in profile.keys()]
            print(f"✅ Loaded {author} from cache ({len(skills)} skills)")
            return set(skills)
    except:
        pass
    return None

def load_multiple_from_cache(authors: list, repo: str = "huggingface/transformers") -> dict:
    """Load multiple authors from cache at once"""
    result = {}
    for author in authors:
        cached = load_from_cache(author, repo)
        if cached is not None and len(cached) > 0:
            result[author] = cached
    return result

def get_cached_author_count(repo: str = "huggingface/transformers") -> int:
    """Get number of authors in cache (approximate)"""
    try:
        checkpoint = load_checkpoint()
        return len([k for k, v in checkpoint.items() if v])
    except:
        return 0

def map_commits_to_skills(commits, max_llm_calls=None, repo="huggingface/transformers", 
                          specific_authors=None, max_authors=None):
    """
    Map commits to skills with crash-safe checkpointing.
    Can filter to specific authors or limit to max_authors.
    """
    global llm_calls_made
    llm_calls_made = 0
    
    # Load existing checkpoint
    checkpoint = load_checkpoint()
    
    # Clean checkpoint - remove empty entries
    cleaned_checkpoint = {k: v for k, v in checkpoint.items() if v}
    if len(cleaned_checkpoint) != len(checkpoint):
        print(f"🧹 Cleaned checkpoint: removed {len(checkpoint) - len(cleaned_checkpoint)} empty entries")
        checkpoint = cleaned_checkpoint
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    
    # Group commits by author
    commits_by_author = defaultdict(list)
    for commit in commits:
        author = commit.get("author", {}).get("login") or commit["commit"]["author"]["name"]
        commits_by_author[author].append(commit)

    # Filter to specific authors if provided
    if specific_authors:
        specific_set = set(specific_authors)
        commits_by_author = {k: v for k, v in commits_by_author.items() if k in specific_set}
        print(f"🎯 Filtered to {len(commits_by_author)} specific authors")
    
    # Limit number of authors if specified
    if max_authors and len(commits_by_author) > max_authors:
        sorted_authors = sorted(commits_by_author.keys(), 
                               key=lambda a: len(commits_by_author[a]), 
                               reverse=True)
        top_authors = sorted_authors[:max_authors]
        commits_by_author = {k: commits_by_author[k] for k in top_authors}
        print(f"📊 Limited to top {len(commits_by_author)} authors by commit count")

    dev_skills = defaultdict(set)
    
    # First, load from checkpoint/cache (only non-empty)
    for author in commits_by_author.keys():
        # Try cache first
        cached = load_from_cache(author, repo)
        if cached is not None and len(cached) > 0:
            dev_skills[author] = cached
        elif author in checkpoint and checkpoint[author]:
            dev_skills[author] = set(checkpoint[author])
            print(f"📋 Loaded {author} from checkpoint ({len(dev_skills[author])} skills)")
    
    # Process only NEW authors (not in cache and not in checkpoint)
    authors_to_process = [
        a for a in commits_by_author.keys() 
        if a not in dev_skills
    ]
    
    # Also re-process authors with empty skills in checkpoint
    authors_with_empty = [a for a in commits_by_author.keys() 
                          if a in checkpoint and not checkpoint[a]]
    if authors_with_empty:
        print(f"\n🔄 Will re-process {len(authors_with_empty)} authors with empty skills")
        authors_to_process.extend(authors_with_empty)
    
    authors_to_process = list(set(authors_to_process))  # Remove duplicates
    
    print(f"\n📊 Summary:")
    print(f"   Total authors: {len(commits_by_author)}")
    print(f"   Already completed with skills: {len(dev_skills)}")
    print(f"   Need to process: {len(authors_to_process)}")
    
    if not authors_to_process:
        print("✅ All authors already cached with skills! Nothing to process.")
        print_rate_limiter_stats()
        return dev_skills
    
    # Process each new author
    for idx, author in enumerate(authors_to_process, 1):
        author_commits = commits_by_author[author]
        print(f"\n🔄 [{idx}/{len(authors_to_process)}] Analyzing {author} ({len(author_commits)} commits)...")
        
        commit_summaries = []
        for commit_idx, commit in enumerate(author_commits):
            try:
                if commit_idx > 0:
                    time.sleep(0.5)  # Small delay between commits
                
                commit_detail = session.get(commit["url"], headers=HEADERS, timeout=15).json()
                commit_message = commit["commit"]["message"]
                files = commit_detail.get("files", [])
                summary = summarize_commit(commit_message, files)
                if summary:
                    commit_summaries.append(f"Commit: {commit_message[:80].replace('\n',' ')}...\nSummary: {summary}")
                    
            except Exception as e:
                print(f"   ⚠️ Error on commit {commit_idx + 1}: {e}")
                continue
        
        # Extract skills from summaries
        author_skills = set()
        if commit_summaries:
            prompt = DEVELOPER_PROFILE_REDUCE_PROMPT.format(
                author=author,
                commit_summaries="\n\n".join(commit_summaries)
            )
            raw_result = call_llm(prompt)
            if raw_result:
                try:
                    json_match = re.search(r'\[.*\]', raw_result, re.DOTALL)
                    skills = json.loads(json_match.group()) if json_match else json.loads(raw_result)
                    if isinstance(skills, list):
                        author_skills = set(skills)
                except Exception as e:
                    print(f"   ⚠️ Failed to parse skills: {e}")
        
        # Save to dev_skills (even if empty, but we'll skip saving empty)
        dev_skills[author] = author_skills
        
        # Only save checkpoint if skills were extracted
        if author_skills:
            save_checkpoint(author, author_skills, repo)
        else:
            print(f"   ⚠️ No skills extracted for {author} - not saving to cache")
        
        print(f"   ✅ Completed {author}: {len(author_skills)} skills extracted")
        print(f"   📊 Progress: {idx}/{len(authors_to_process)} authors processed")
        print(f"   📞 LLM calls made so far: {llm_calls_made}")
    
    print(f"\n✅ Complete! Processed {len(dev_skills)} total developers")
    
    # Print rate limiter stats
    print_rate_limiter_stats()
    
    return dev_skills
# Add this helper function to get commit history without LLM
def fetch_commit_history_for_author(author: str, owner: str, repo: str, limit: int = 50) -> List[dict]:
    """Fetch commit history for a specific author from GitHub API."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/commits"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    
    collected = []
    page = 1
    
    while len(collected) < limit:
        resp = session.get(
            url,
            headers=headers,
            params={"author": author, "per_page": min(100, limit - len(collected)), "page": page},
            timeout=15,
        )
        if resp.status_code != 200:
            break
        
        batch = resp.json() or []
        if not batch:
            break
        
        for commit in batch:
            try:
                detail = session.get(commit["url"], headers=headers, timeout=15).json()
                commit["files"] = detail.get("files", [])
            except:
                commit["files"] = []
            collected.append(commit)
        
        if len(batch) < 100:
            break
        page += 1
    
    return collected[:limit]

def fetch_commit_history_bulk(authors: List[str], owner: str, repo: str, limit: int = 50) -> Dict[str, List[dict]]:
    """
    Fetch commit history for multiple authors in parallel.
    NO LLM calls - pure GitHub API.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_author = {
            executor.submit(fetch_commit_history_for_author, author, owner, repo, limit): author 
            for author in authors
        }
        
        for future in as_completed(future_to_author):
            author = future_to_author[future]
            try:
                commits = future.result()
                results[author] = commits
                print(f"  📡 Fetched {len(commits)} commits for {author} from GitHub")
            except Exception as e:
                print(f"  ⚠️ Failed to fetch commits for {author}: {e}")
                results[author] = []
    
    return results