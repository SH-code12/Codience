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
from codience.src.Reviewer_Recommender.Process.llm import generate_with_resilience
from codience.src.Reviewer_Recommender.Process.prompts import FILE_DIFF_SUMMARY_PROMPT, COMMIT_CHUNK_SUMMARY_PROMPT, DEVELOPER_PROFILE_REDUCE_PROMPT

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
BASE_URL = "https://api.github.com"

session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

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

# Global counter to avoid burning through API budget
LLM_BUDGET = 100
llm_calls_made = 0
SUMMARY_WORKERS = int(os.getenv("SUMMARY_WORKERS", "2"))

def call_llm(prompt, retries=3):
    global llm_calls_made
    if llm_calls_made >= LLM_BUDGET:
        return "Budget exceeded"

    llm_calls_made += 1
    result = generate_with_resilience(prompt, purpose="history_summary", max_retries=retries)
    if result.get("ok"):
        return result.get("text", "")
    return ""

def summarize_file_patch(file_data):
    if not file_data.get("patch"): return ""
    prompt = FILE_DIFF_SUMMARY_PROMPT.format(
        filename=file_data['filename'],
        patch=file_data['patch']
    )
    res = call_llm(prompt)
    if not res or res == "Budget exceeded": return ""
    return f"File: {file_data['filename']}\nSummary: {res}"

def summarize_commit(commit_message, files):
    # 1. Map step: Summarize each file
    valid_files = [f for f in files if "patch" in f and not f["filename"].endswith(".csv") and not f["filename"].endswith("lock.json") and not f["filename"].endswith("poetry.lock")]
    
    file_summaries = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=SUMMARY_WORKERS) as executor:
        results = executor.map(summarize_file_patch, valid_files)
        for r in results:
            if r: file_summaries.append(r)
            
    if not file_summaries:
        return ""
        
    # 2. Reduce step: Summarize the whole commit
    prompt = COMMIT_CHUNK_SUMMARY_PROMPT.format(
        commit_message=commit_message,
        file_summaries="\n\n".join(file_summaries)
    )
    return call_llm(prompt)

def map_commits_to_skills(commits, max_llm_calls=100):
    global llm_calls_made
    llm_calls_made = 0  # reset budget for this run
    # Optionally limit total LLM calls
    global LLM_BUDGET
    LLM_BUDGET = max_llm_calls

    commits_by_author = defaultdict(list)
    for commit in commits:
        author = commit.get("author", {}).get("login") or commit["commit"]["author"]["name"]
        commits_by_author[author].append(commit)

    dev_skills = defaultdict(set)

    for author, author_commits in commits_by_author.items():
        print(f"🔄 Analyzing history for {author} ({len(author_commits)} commits)...")
        commit_summaries = []
        for commit in author_commits:
            try:
                # Fetch detailed commit data (including file patches)
                commit_detail = session.get(commit["url"], headers=HEADERS, timeout=15).json()
                commit_message = commit["commit"]["message"]
                files = commit_detail.get("files", [])
                # Summarize this single commit (Map step)
                summary = summarize_commit(commit_message, files)
                if summary and summary != "Budget exceeded":
                    commit_summaries.append(f"Commit: {commit_message[:80].replace('\n',' ')}...\nSummary: {summary}")
                time.sleep(0.5)  # basic rate‑limit protection for GitHub
            except Exception as e:
                print(f"⚠️ Error processing commit {commit.get('sha','')}: {e}")
                continue
        # Reduce step: build a developer skill profile from the commit summaries
        if commit_summaries:
            prompt = DEVELOPER_PROFILE_REDUCE_PROMPT.format(
                author=author,
                commit_summaries="\n\n".join(commit_summaries)
            )
            raw_result = call_llm(prompt)
            try:
                json_match = re.search(r'\[.*\]', raw_result, re.DOTALL)
                skills = json.loads(json_match.group()) if json_match else json.loads(raw_result)
                if isinstance(skills, list):
                    for skill in skills:
                        dev_skills[author].add(skill)
            except Exception as e:
                print(f"⚠️ Failed to parse skill JSON for {author}: {e}")
    return dev_skills