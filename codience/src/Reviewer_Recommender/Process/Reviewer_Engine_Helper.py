import os
import time
import requests
import json
import re
import concurrent.futures
from collections import defaultdict
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from codience.src.Reviewer_Recommender.Data.commit_diff_vectordb import index_commits_to_db

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

EXT_TO_SKILL = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "React/TypeScript", 
    ".jsx": "React", ".cs": "C#/.NET", ".java": "Java", ".go": "Go", ".rb": "Ruby", 
    ".php": "PHP", ".html": "HTML", ".css": "CSS", ".sql": "SQL", ".sh": "Shell", 
    ".rs": "Rust", ".cpp": "C++", ".c": "C", ".yml": "CI/CD", ".yaml": "CI/CD", 
    "Dockerfile": "Docker", "docker-compose": "Docker"
}

KEYWORD_TO_SKILL = {
    "auth": "Authentication", "security": "Security", "db": "Database", "sql": "SQL", 
    "api": "API Development", "performance": "Performance Optimization", "docker": "Docker", 
    "k8s": "Kubernetes", "test": "Testing/QA", "react": "React", "vue": "Vue", 
    "aws": "AWS", "azure": "Azure", "gcp": "GCP", "pipeline": "CI/CD", "refactor": "Refactoring"
}

def extract_skills_heuristically(commit_message, files):
    skills = set()
    msg_lower = commit_message.lower()
    for kw, skill in KEYWORD_TO_SKILL.items():
        if re.search(r'\b' + kw + r'\b', msg_lower):
            skills.add(skill)
            
    for f in files:
        filename = f.get("filename", "").lower()
        if not filename:
            continue
        
        # Check extensions
        _, ext = os.path.splitext(filename)
        if ext in EXT_TO_SKILL:
            skills.add(EXT_TO_SKILL[ext])
        
        # Check specific filenames/paths
        if "dockerfile" in filename:
            skills.add("Docker")
        if "workflows" in filename and (ext == ".yml" or ext == ".yaml"):
            skills.add("GitHub Actions")
            
    return skills

def analyze_user_commit_history(author: str, author_commits: list[dict], max_llm_calls=None) -> list[str]:
    print(f"🔄 Extracting skills & Vector Indexing history for {author} ({len(author_commits)} commits)...")
    dev_skills = set()
    for commit in author_commits:
        try:
            commit_detail = session.get(commit["url"], headers=HEADERS, timeout=15).json()
            commit_message = commit["commit"]["message"]
            files = commit_detail.get("files", [])
            skills = extract_skills_heuristically(commit_message, files)
            dev_skills.update(skills)
            
            # Prepare data for Vector DB RAG Indexing
            to_index = []
            for f in files:
                if f.get("patch"):
                    to_index.append({
                        "author": author,
                        "sha": commit.get("sha", "unknown"),
                        "filename": f.get("filename", "unknown"),
                        "patch": f.get("patch")
                    })
            if to_index:
                index_commits_to_db(to_index)
                
            time.sleep(0.1) # Just to avoid aggressive GitHub API limits
        except Exception as e:
            print(f"⚠️ Error processing commit {commit.get('sha','')}: {e}")
            continue

    return list(dev_skills)

def map_commits_to_skills(commits, max_llm_calls=None):
    commits_by_author = defaultdict(list)
    for commit in commits:
        author = commit.get("author", {}).get("login") or commit["commit"]["author"]["name"]
        commits_by_author[author].append(commit)

    dev_skills = defaultdict(set)

    for author, author_commits in commits_by_author.items():
        print(f"🔄 Extracting skills & Vector Indexing history for {author} ({len(author_commits)} commits)...")
        for commit in author_commits:
            try:
                commit_detail = session.get(commit["url"], headers=HEADERS, timeout=15).json()
                commit_message = commit["commit"]["message"]
                files = commit_detail.get("files", [])
                skills = extract_skills_heuristically(commit_message, files)
                dev_skills[author].update(skills)
                
                # Prepare data for Vector DB RAG Indexing
                to_index = []
                for f in files:
                    if f.get("patch"):
                        to_index.append({
                            "author": author,
                            "sha": commit.get("sha", "unknown"),
                            "filename": f.get("filename", "unknown"),
                            "patch": f.get("patch")
                        })
                if to_index:
                    index_commits_to_db(to_index)
                    
                time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ Error processing commit {commit.get('sha','')}: {e}")
                continue
                
    return dev_skills