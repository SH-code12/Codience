import os
import time
import requests
from collections import defaultdict
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
BASE_URL = "https://api.github.com"

session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

def fetch_commits(owner, repo, per_page=30):
    url = f"{BASE_URL}/repos/{owner}/{repo}/commits"
    try:
        r = session.get(url, headers=HEADERS, params={"per_page": per_page}, timeout=15)
        return r.json() if r.status_code == 200 else []
    except: return []

def detect_skill_from_file(file):
    ext = file.split('.')[-1].lower() if '.' in file else ""
    mapping = {
        "py": "Python", "cs": ".NET", "js": "JavaScript", "ts": "TypeScript",
        "jsx": "React", "tsx": "React", "java": "Java", "sql": "SQL"
    }
    return mapping.get(ext)

def map_commits_to_skills(commits):
    dev_skills = defaultdict(set)
    for commit in commits:
        author = commit.get("author", {}).get("login") or commit["commit"]["author"]["name"]
        try:
            data = session.get(commit["url"], headers=HEADERS, timeout=15).json()
            for f in data.get("files", []):
                skill = detect_skill_from_file(f["filename"])
                if skill: dev_skills[author].add(skill)
            time.sleep(0.2) # Avoid rate limits
        except: continue
    return dev_skills