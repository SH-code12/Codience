import os
import requests
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from .analysis_PR import extract_pr_skills

# Import your history logic - UPDATED IMPORT
from .commit_history_utils import fetch_commits, map_commits_to_skills, load_from_cache, get_cached_author_count, load_multiple_from_cache, fetch_commit_history_for_author

# Import AI Agents
from .scorer_agent import calculate_match_scores
from ..Data.searching_into_vectordb import search_vector_db
from ..Data.commit_diff_vectordb import search_similar_commits
from .profile_cache import ProfileCache

load_dotenv()

# GitHub session for API calls
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
BASE_URL = "https://api.github.com"

# --- 1. FETCH REAL DATA ---
def fetch_real_pr_data(owner, repo, pr_number):
    print(f"📡 Fetching Real PR #{pr_number} from {owner}/{repo}...")
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json" 
    }
    
    pr_resp = requests.get(pr_url, headers=headers)
    if pr_resp.status_code != 200:
        print(f"❌ Failed to fetch PR info: {pr_resp.status_code}")
        try:
            print(f"GitHub Error: {pr_resp.json().get('message')}")
        except:
            print(f"Raw Response: {pr_resp.text}")
        return None
        
    pr_json = pr_resp.json()
    
    files_url = f"{pr_url}/files"
    files_resp = requests.get(files_url, headers=headers)
    files_data = []
    if files_resp.status_code == 200:
        files_json = files_resp.json()
        for f in files_json:
            if "patch" in f and not f["filename"].endswith("lock.json") and not f["filename"].endswith("poetry.lock"):
                files_data.append({
                    "filename": f["filename"],
                    "patch": f["patch"]
                })
        files_data = files_data[:30]
    else:
        print(f"⚠️ Failed to fetch PR files: {files_resp.status_code}")
    
    return {
        "title": pr_json.get("title"),
        "description": pr_json.get("body") or "No description provided.",
        "files": files_data 
    }


def fetch_repo_contributors(owner, repo, max_pages=5, per_page=100):
    contributors = set()
    headers = {
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json",
    }

    for page in range(1, max_pages + 1):
        url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
        resp = requests.get(url, headers=headers, params={"per_page": per_page, "page": page}, timeout=20)
        if resp.status_code != 200:
            if page == 1:
                print(f"⚠️ Could not fetch contributors list: {resp.status_code}")
            break

        items = resp.json() or []
        if not items:
            break

        for item in items:
            login = (item or {}).get("login")
            if login:
                contributors.add(login)

        if len(items) < per_page:
            break

    return contributors


# --- THE ENGINE ---
class ReviewerRecommender:
    DEFAULT_TOP_K = 5
    DEFAULT_PRIORITIZE_RECENT_ACTIVITY = True
    DEFAULT_COMMITS_PER_REVIEWER = 50

    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo
        self.indexed_commits = []
        self.history_profiles = {}
        self.commit_history_cache = {}  # Store commit history for Tversky
        self.contributor_stats = {}
        self.repo_contributors = set()
        self._profile_cache = ProfileCache()

    def initialize_with_cache_check(self, required_developers: Optional[List[str]] = None, 
                                    max_developers: int = 50, 
                                    max_commits: int = 500,
                                    commits_per_reviewer: int = 50,
                                    force_refresh: bool = False) -> bool:
        """
        Smart initialization: 
        - Skills: Load from cache when available (NO LLM)
        - Commit history: Always fetch from GitHub for Tversky (NO LLM, just API)
        """
        repo_key = f"{self.owner}/{self.repo}"
        
        if force_refresh:
            print(f"🔄 Force refresh mode - ignoring cache")
            return self._initialize_fresh(max_developers, max_commits)
        
        # Fetch repo contributors (lightweight, no LLM)
        self.repo_contributors = fetch_repo_contributors(self.owner, self.repo)
        
        if required_developers:
            return self._initialize_specific_developers(required_developers, commits_per_reviewer, max_commits)
        else:
            return self._initialize_top_developers(max_developers, max_commits, commits_per_reviewer)
    
    def _initialize_specific_developers(self, required_developers: List[str], 
                                        commits_per_reviewer: int,
                                        max_commits: int) -> bool:
        """Initialize for specific developers - skills from cache, commits from GitHub"""
        needed_set = set(required_developers)
        print(f"🎯 Need {len(needed_set)} specific developers: {', '.join(list(needed_set)[:5])}...")
        
        # Step 1: Load skills from cache (NO LLM)
        print(f"\n📦 Loading skills from cache...")
        cached_profiles = load_multiple_from_cache(list(needed_set), f"{self.owner}/{self.repo}")
        cached_developers = set(cached_profiles.keys())
        missing_developers = needed_set - cached_developers
        
        print(f"📊 Cache status:")
        print(f"   ✅ Skills in cache: {len(cached_developers)} developers")
        print(f"   ❌ Skills missing: {len(missing_developers)} developers")
        
        self.history_profiles.update(cached_profiles)
        
        # Step 2: ALWAYS fetch commit history from GitHub for ALL developers (for Tversky)
        print(f"\n📡 Fetching commit history from GitHub for all {len(needed_set)} developers...")
        all_commit_history = self._fetch_commits_bulk(list(needed_set), commits_per_reviewer)
        
        # Store commit history for Tversky
        self.commit_history_cache = all_commit_history
        self.indexed_commits = []
        for author, commits in all_commit_history.items():
            for commit in commits:
                self.indexed_commits.append(commit)
        
        # Step 3: Process missing developers with LLM (skills only)
        if missing_developers:
            print(f"\n⚠️ Need to extract skills for {len(missing_developers)} developers (LLM calls required)")
            
            # Get commits only for missing developers
            missing_commits = []
            for author in missing_developers:
                if author in all_commit_history:
                    for commit in all_commit_history[author]:
                        missing_commits.append(commit)
            
            # Extract skills using LLM (only for missing authors)
            repo_key = f"{self.owner}/{self.repo}"
            new_skills = map_commits_to_skills(
                missing_commits, 
                repo=repo_key,
                specific_authors=list(missing_developers)
            )
            self.history_profiles.update(new_skills)
        
        # Build contributor stats
        self.contributor_stats = self._build_contributor_stats(self.indexed_commits)
        
        if not missing_developers:
            print(f"\n🎉 ALL skills loaded from cache! ZERO LLM calls made!")
            print(f"📊 Tversky will use {len(self.indexed_commits)} commits from GitHub")
            return True
        else:
            print(f"\n⚠️ Processed {len(missing_developers)} authors with LLM")
            print(f"📊 Total commits for Tversky: {len(self.indexed_commits)}")
            return False
    
    def _initialize_top_developers(self, max_developers: int, max_commits: int, commits_per_reviewer: int) -> bool:
        """Initialize for top developers - skills from cache, commits from GitHub"""
        print(f"🎯 Need top {max_developers} most active developers")
        
        # Step 1: Fetch commits to identify top developers
        print(f"\n📡 Fetching commits from GitHub to identify top developers...")
        commits = fetch_commits(self.owner, self.repo, limit=max_commits)
        
        # Group commits by author
        commits_by_author = defaultdict(list)
        for commit in commits:
            author = commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name")
            if author:
                commits_by_author[author].append(commit)
        
        # Sort by commit count
        sorted_authors = sorted(commits_by_author.keys(), 
                               key=lambda a: len(commits_by_author[a]), 
                               reverse=True)
        top_authors = sorted_authors[:max_developers]
        
        # Step 2: Load skills from cache (NO LLM)
        print(f"\n📦 Loading skills from cache for {len(top_authors)} authors...")
        cached_profiles = load_multiple_from_cache(top_authors, f"{self.owner}/{self.repo}")
        cached_developers = set(cached_profiles.keys())
        missing_developers = [a for a in top_authors if a not in cached_developers]
        
        print(f"📊 Cache status:")
        print(f"   ✅ Skills in cache: {len(cached_developers)} developers")
        print(f"   ❌ Skills missing: {len(missing_developers)} developers")
        
        self.history_profiles.update(cached_profiles)
        
        # Step 3: ALWAYS fetch commit history from GitHub for ALL top developers (for Tversky)
        print(f"\n📡 Fetching commit history from GitHub for all {len(top_authors)} developers...")
        all_commit_history = self._fetch_commits_bulk(top_authors, commits_per_reviewer)
        
        # Store commit history for Tversky
        self.commit_history_cache = all_commit_history
        self.indexed_commits = []
        for author, commits in all_commit_history.items():
            for commit in commits:
                self.indexed_commits.append(commit)
        
        # Step 4: Process missing developers with LLM (skills only)
        if missing_developers:
            print(f"\n⚠️ Need to extract skills for {len(missing_developers)} developers (LLM calls required)")
            
            # Get commits only for missing developers
            missing_commits = []
            for author in missing_developers:
                if author in all_commit_history:
                    for commit in all_commit_history[author]:
                        missing_commits.append(commit)
            
            # Extract skills using LLM (only for missing authors)
            repo_key = f"{self.owner}/{self.repo}"
            new_skills = map_commits_to_skills(
                missing_commits, 
                repo=repo_key,
                specific_authors=missing_developers
            )
            self.history_profiles.update(new_skills)
        
        # Build contributor stats
        self.contributor_stats = self._build_contributor_stats(self.indexed_commits)
        
        if not missing_developers:
            print(f"\n🎉 ALL skills loaded from cache! ZERO LLM calls made!")
            print(f"📊 Tversky will use {len(self.indexed_commits)} commits from GitHub")
            return True
        else:
            print(f"\n⚠️ Processed {len(missing_developers)} authors with LLM")
            print(f"📊 Total commits for Tversky: {len(self.indexed_commits)}")
            return False
    
    def _fetch_commits_bulk(self, authors: List[str], limit: int = 50) -> Dict[str, List[dict]]:
        """Fetch commit history for multiple authors in parallel"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_author = {
                executor.submit(self._fetch_commits_for_author_with_files, author, limit): author 
                for author in authors
            }
            
            for future in as_completed(future_to_author):
                author = future_to_author[future]
                try:
                    commits = future.result()
                    results[author] = commits
                    print(f"  📡 Fetched {len(commits)} commits for {author}")
                except Exception as e:
                    print(f"  ⚠️ Failed to fetch commits for {author}: {e}")
                    results[author] = []
        
        return results
    
    def _fetch_commits_for_author_with_files(self, author_name: str, limit: int = 50) -> List[dict]:
        """Fetch commits for an author with file details included"""
        target = max(0, int(limit))
        if target <= 0:
            return []
        
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits"
        headers = {
            "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        collected = []
        page = 1
        
        while len(collected) < target:
            batch_size = min(100, target - len(collected))
            resp = requests.get(
                url,
                headers=headers,
                params={"author": author_name, "per_page": batch_size, "page": page},
                timeout=20,
            )
            if resp.status_code != 200:
                break
            
            batch = resp.json() or []
            if not isinstance(batch, list) or not batch:
                break
            
            # Fetch file details for each commit
            for commit in batch:
                try:
                    detail_url = commit.get("url")
                    if detail_url:
                        detail_resp = requests.get(detail_url, headers=headers, timeout=15)
                        if detail_resp.status_code == 200:
                            detail = detail_resp.json()
                            commit["files"] = detail.get("files", [])
                        else:
                            commit["files"] = []
                except:
                    commit["files"] = []
                collected.append(commit)
            
            if len(batch) < batch_size:
                break
            page += 1
        
        return collected[:target]
    
    def _process_specific_developers(self, developers: Set[str], commits_per_reviewer: int, max_commits: int):
        """Process only specific developers (legacy - kept for compatibility)"""
        print(f"🚀 Processing {len(developers)} specific developers...")
        
        all_commits = []
        seen_shas = set()
        
        for username in developers:
            fetched = self._fetch_commits_for_author(username, commits_per_reviewer)
            for commit in fetched:
                sha = commit.get("sha")
                if sha and sha in seen_shas:
                    continue
                if sha:
                    seen_shas.add(sha)
                all_commits.append(commit)
        
        self.indexed_commits = all_commits
        self.contributor_stats.update(self._build_contributor_stats(all_commits))
        
        # Only map skills for these specific developers
        repo_key = f"{self.owner}/{self.repo}"
        new_profiles = map_commits_to_skills(all_commits, repo=repo_key, specific_authors=list(developers))
        
        # Update existing profiles
        for author, skills in new_profiles.items():
            self.history_profiles[author] = skills
        
        print(f"✅ Processed {len(new_profiles)} new developers")
    
    def _process_top_developers(self, max_developers: int, max_commits: int, need_to_process: int):
        """Process only the top N developers we need (legacy - kept for compatibility)"""
        print(f"🚀 Fetching top {max_developers} developers (need {need_to_process} new ones)...")
        
        # Fetch commits and get top developers
        commits = fetch_commits(self.owner, self.repo, limit=max_commits)
        
        # Group commits by author
        commits_by_author = defaultdict(list)
        for commit in commits:
            author = commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name")
            if author:
                commits_by_author[author].append(commit)
        
        # Sort by commit count
        sorted_authors = sorted(commits_by_author.keys(), 
                               key=lambda a: len(commits_by_author[a]), 
                               reverse=True)
        
        # Take top N developers
        top_authors = sorted_authors[:max_developers]
        
        # Filter out already cached developers
        repo_key = f"{self.owner}/{self.repo}"
        
        # Filter commits to only top authors
        filtered_commits = []
        for commit in commits:
            author = commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name")
            if author in top_authors:
                filtered_commits.append(commit)
        
        # Process these commits (will auto-skip already cached)
        self.indexed_commits = filtered_commits
        self.contributor_stats.update(self._build_contributor_stats(filtered_commits))
        
        new_profiles = map_commits_to_skills(filtered_commits, repo=repo_key, max_authors=need_to_process)
        
        # Update existing profiles
        for author, skills in new_profiles.items():
            self.history_profiles[author] = skills
        
        print(f"✅ Added {len(new_profiles)} new developers to cache")
    
    def _initialize_fresh(self, max_developers: int, max_commits: int):
        """Fresh initialization (ignore cache)"""
        print(f"🚀 Building Knowledge Base from scratch...")
        self.repo_contributors = fetch_repo_contributors(self.owner, self.repo)
        commits = fetch_commits(self.owner, self.repo, limit=max_commits)
        
        # Group commits by author and count
        commits_by_author = defaultdict(list)
        for commit in commits:
            author = commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name")
            if author:
                commits_by_author[author].append(commit)
        
        # Sort by commit count (most active first)
        sorted_authors = sorted(commits_by_author.keys(), 
                            key=lambda a: len(commits_by_author[a]), 
                            reverse=True)
        
        # Take only top max_developers
        top_authors = sorted_authors[:max_developers]
        print(f"📊 Processing top {len(top_authors)} developers (out of {len(sorted_authors)})")
        
        # Filter commits to only top developers
        filtered_commits = []
        for commit in commits:
            author = commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name")
            if author in top_authors:
                filtered_commits.append(commit)
        
        self.indexed_commits = filtered_commits
        self.contributor_stats = self._build_contributor_stats(filtered_commits)
        
        repo_key = f"{self.owner}/{self.repo}"
        self.history_profiles = map_commits_to_skills(filtered_commits, repo=repo_key)

        for author in self.contributor_stats:
            self.history_profiles.setdefault(author, set())

        print(f"✅ Indexed {len(self.history_profiles)} developers.")
        return False
    
    def initialize_system(self, max_commits=500, max_llm_calls=None, max_developers=50):
        """DEPRECATED: Use initialize_with_cache_check instead"""
        print("⚠️ initialize_system is deprecated. Use initialize_with_cache_check for smart caching.")
        return self._initialize_fresh(max_developers, max_commits)
    
    def initialize_for_required_only(self, required_reviewers, commits_per_reviewer=50, max_llm_calls=20):
        """DEPRECATED: Use initialize_with_cache_check instead"""
        print("⚠️ initialize_for_required_only is deprecated. Use initialize_with_cache_check for smart caching.")
        return self._initialize_specific_developers(required_reviewers, commits_per_reviewer, 500)
    
    def _parse_commit_datetime(self, date_value):
        if not date_value:
            return None
        try:
            normalized = date_value.replace("Z", "+00:00") if isinstance(date_value, str) else date_value
            return datetime.fromisoformat(normalized)
        except Exception:
            return None

    def _build_contributor_stats(self, commits):
        now = datetime.now(timezone.utc)
        by_author = {}

        for commit in commits:
            author = commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name")
            if not author:
                continue

            date_value = commit.get("commit", {}).get("author", {}).get("date")
            parsed_date = self._parse_commit_datetime(date_value)
            by_author.setdefault(author, {"count": 0, "dates": []})
            by_author[author]["count"] += 1
            if parsed_date:
                by_author[author]["dates"].append(parsed_date)

        stats = {}
        for author, data in by_author.items():
            dates = data["dates"]
            commits_count = data["count"]

            if dates:
                first_seen = min(dates)
                last_seen = max(dates)
                tenure_days = max((now - first_seen).days, 0)
                recency_days = max((now - last_seen).days, 0)
            else:
                tenure_days = 365
                recency_days = 365

            recency_score = max(0.0, 1.0 - (min(recency_days, 90) / 90.0))

            stats[author] = {
                "commit_count": commits_count,
                "tenure_days": tenure_days,
                "recency_days": recency_days,
                "recency_score": round(recency_score, 4),
            }

        return stats

    def _limit_commits_per_reviewer(self, commits, commits_per_reviewer):
        if commits_per_reviewer <= 0:
            return commits

        limited = []
        author_counts = {}
        for commit in commits or []:
            author = commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name")
            if not author:
                continue

            current_count = author_counts.get(author, 0)
            if current_count >= commits_per_reviewer:
                continue

            author_counts[author] = current_count + 1
            limited.append(commit)

        return limited

    def _normalize_required_reviewers(self, required_reviewers):
        required_map = {}
        for reviewer in required_reviewers or []:
            if isinstance(reviewer, str):
                clean_name = reviewer.strip()
                if not clean_name: continue
                key = clean_name.lower()
                required_map[key] = {
                    "username": clean_name,
                    "raw_skills": []
                }
            elif isinstance(reviewer, dict):
                username = reviewer.get("username") or reviewer.get("login")
                if not username: continue
                key = username.strip().lower()
                required_map[key] = {
                    "username": username.strip(),
                    "raw_skills": reviewer.get("raw_skills", [])
                }
        return required_map

    def _count_commits_for_author(self, commits, author_name):
        target = (author_name or "").lower()
        if not target:
            return 0

        count = 0
        for commit in commits or []:
            author = commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name")
            if author and author.lower() == target:
                count += 1
        return count

    def _fetch_commits_for_author(self, author_name, limit):
        """Legacy method - kept for compatibility"""
        target = max(0, int(limit or 0))
        if target <= 0:
            return []

        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits"
        headers = {
            "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
            "Accept": "application/vnd.github.v3+json",
        }

        collected = []
        page = 1
        while len(collected) < target:
            batch_size = min(100, target - len(collected))
            resp = requests.get(
                url,
                headers=headers,
                params={"author": author_name, "per_page": batch_size, "page": page},
                timeout=20,
            )
            if resp.status_code != 200:
                print(f"⚠️ Could not fetch commits for required reviewer {author_name}: {resp.status_code}")
                break

            batch = resp.json() or []
            if not isinstance(batch, list) or not batch:
                break

            collected.extend(batch)
            if len(batch) < batch_size:
                break
            page += 1

        return collected[:target]

    def _ensure_required_reviewers_history(self, required_names, commits_per_reviewer):
        if commits_per_reviewer <= 0:
            return

        extra_commits = []
        seen_shas = {c.get("sha") for c in self.indexed_commits if c.get("sha")}

        for required_name in required_names:
            existing_count = self._count_commits_for_author(self.indexed_commits, required_name)
            missing = commits_per_reviewer - existing_count
            if missing <= 0:
                continue

            fetched = self._fetch_commits_for_author(required_name, missing)
            for commit in fetched:
                sha = commit.get("sha")
                if sha and sha in seen_shas:
                    continue
                if sha:
                    seen_shas.add(sha)
                extra_commits.append(commit)

        if not extra_commits:
            return

        self.indexed_commits.extend(extra_commits)

        updated_stats = self._build_contributor_stats(self.indexed_commits)
        self.contributor_stats.update(updated_stats)

        extra_profiles = map_commits_to_skills(extra_commits, max_llm_calls=10)
        for author, skills in extra_profiles.items():
            self.history_profiles.setdefault(author, set())
            self.history_profiles[author].update(skills)

    def _resolve_valid_required_contributors(self, required_map):
        if not required_map:
            return []
        return [r["username"] for r in required_map.values()]

    def recommend(self, pr_data):
        v2_result = self.recommend_v2(pr_data, required_reviewers=[], options={})
        return v2_result.get("recommended_reviewers", [])

    def recommend_v2(self, pr_data, required_reviewers=None, options=None):
        options = options or {}
        raw_top_k = options.get("top_k")
        top_k = self.DEFAULT_TOP_K if raw_top_k is None else max(1, min(20, int(raw_top_k)))
        raw_prioritize = options.get("prioritize_recent_activity")
        if raw_prioritize is None:
            prioritize_recent_activity = self.DEFAULT_PRIORITIZE_RECENT_ACTIVITY
        else:
            prioritize_recent_activity = bool(raw_prioritize)
        raw_commits_per_reviewer = options.get("commits_per_reviewer")
        commits_per_reviewer = (
            self.DEFAULT_COMMITS_PER_REVIEWER
            if raw_commits_per_reviewer is None
            else max(1, min(100, int(raw_commits_per_reviewer)))
        )

        limited_commits = self._limit_commits_per_reviewer(self.indexed_commits, commits_per_reviewer)
        dynamic_stats = self._build_contributor_stats(limited_commits)

        required_map = self._normalize_required_reviewers(required_reviewers)
        required_set = set(required_map.keys())
        required_only_mode = bool(required_map)

        valid_required_contributors = self._resolve_valid_required_contributors(required_map)
        self._ensure_required_reviewers_history(valid_required_contributors, commits_per_reviewer)

        limited_commits = self._limit_commits_per_reviewer(self.indexed_commits, commits_per_reviewer)
        dynamic_stats = self._build_contributor_stats(limited_commits)

        # 1. PR Analyzer Agent
        analysis = extract_pr_skills(pr_data)
        required_languages = {lang.strip().title() for lang in analysis.get('detected_languages', [])}
        
        if "C#" in required_languages:
            required_languages.remove("C#")
            required_languages.add(".NET")

        # 2. Vector DB RAG Search (Semantic Candidate Retrieval)
        pr_patches = [f.get("patch", "") for f in pr_data.get("files", []) if f.get("patch")]
        combined_patch = "\n".join(pr_patches)[:3000] # Limit size for embedding
        
        vector_db_candidates = {}
        rag_roles = []
        if combined_patch:
            try:
                # Get top 20 matching commit chunks
                similar_commits = search_similar_commits(combined_patch, k=20)
                for doc in similar_commits:
                    author = doc.metadata.get("author")
                    if author:
                        vector_db_candidates.setdefault(author, []).append(doc.page_content)
                print(f"🔍 Vector DB found historically matched authors: {list(vector_db_candidates.keys())}")
            except Exception as e:
                print(f"⚠️ Vector DB Commit Search Failed: {e}")

        # 3. Preliminary candidate scoring
        if required_only_mode:
            candidate_names = set()
            for key, meta in required_map.items():
                candidate_names.add(meta["username"])
        else:
            observed_contributors = set(self.history_profiles.keys()) | set(dynamic_stats.keys())
            repo_contributors = set(self.repo_contributors)
            candidate_names = set(observed_contributors)
            if repo_contributors:
                candidate_names = {name for name in candidate_names if name in repo_contributors}
            # Add Vector DB authors to the pool
            for author in vector_db_candidates:
                if author not in candidate_names and (not repo_contributors or author in repo_contributors):
                    candidate_names.add(author)

        preliminary_candidates = []
        
        # Build commit history for each candidate from fetched commits (NOT from cache)
        commits_by_author = defaultdict(list)
        
        # Use the commit history we fetched from GitHub
        for author, commits_list in self.commit_history_cache.items():
            for commit in commits_list:
                files = commit.get("files", [])
                if isinstance(files, list):
                    file_paths = [f.get("filename", "") for f in files if isinstance(f, dict) and f.get("filename")]
                    if file_paths:
                        commits_by_author[author].append({
                            "files": file_paths,
                            "date": commit.get("commit", {}).get("author", {}).get("date", "")
                        })
        
        # Also check indexed_commits as fallback
        for commit in self.indexed_commits:
            author = commit.get("author", {}).get("login") or commit.get("commit", {}).get("author", {}).get("name")
            if author and author not in commits_by_author:
                files = [f.get("filename") for f in commit.get("files", []) if f.get("filename")]
                commit_date = commit.get("commit", {}).get("author", {}).get("date", "")
                if files:
                    commits_by_author[author].append({
                        "files": files,
                        "date": commit_date
                    })
        
        for name in candidate_names:
            dev_skills = set(self.history_profiles.get(name, set()))
            matched_skills = required_languages.intersection(dev_skills) if required_languages else set()
            skill_score = len(matched_skills) / max(len(required_languages), 1) if required_languages else (1.0 if dev_skills else 0.0)

            stat = dynamic_stats.get(name, self.contributor_stats.get(name, {}))
            recency_score = stat.get("recency_score", 0.0)
            
            meta = required_map.get(name.lower(), {})
            required_flag = bool(meta)
            raw_skills = meta.get("raw_skills", [])

            base_composite = skill_score
            if prioritize_recent_activity:
                base_composite = (0.55 * skill_score) + (0.45 * recency_score)
            if required_flag:
                base_composite = min(1.0, base_composite + 0.10)

            # Boost if found in Vector DB
            rag_code_matches = vector_db_candidates.get(name, [])
            if rag_code_matches:
                boost = min(0.20, len(rag_code_matches) * 0.05) # +0.05 per chunk match, max 0.20
                base_composite = min(1.0, base_composite + boost)

            # Get commit history for this candidate
            candidate_commit_history = commits_by_author.get(name, [])
            
            preliminary_candidates.append({
                "name": name,
                "commit_history": candidate_commit_history,  # Now has file paths for Tversky!
                "commit_skills": sorted(list(dev_skills)),
                "matched_skills": list(matched_skills),
                "skill_score": round(skill_score, 4),
                "recency_score": recency_score,
                "required_reviewer": required_flag,
                "raw_skills": raw_skills,
                "rag_code_matches": rag_code_matches,
                "prelim_score": round(base_composite, 4),
                "commit_count": stat.get("commit_count", 0),
                "tenure_days": stat.get("tenure_days", 365),
            })
            
        preliminary_candidates = sorted(preliminary_candidates, key=lambda x: x['prelim_score'], reverse=True)
        
        # === TOP 10 PRE-FILTERING (LLM BOTTLENECK FIX) ===
        if not required_only_mode and len(preliminary_candidates) > 10:
            print(f"🔪 Truncating candidates from {len(preliminary_candidates)} to Top 10 to save LLM tokens.")
            preliminary_candidates = preliminary_candidates[:10]
            # Update candidate_names so debug output below matches what is sent to LLM
            candidate_names = {c["name"] for c in preliminary_candidates}

        # 5. Get PR file paths for Tversky scoring
        pr_file_paths = [f.get("filename") for f in pr_data.get("files", []) if f.get("filename")]
        
        # 6. Scorer Matchmaker Agent with Tversky + Formula
        print("🧠 Calculating AI Confidence Scores with Tversky formula...")
        # Add this debug before calling calculate_match_scores
        print("\n🔍 DEBUG: Checking commit history for candidates:")
        for name in candidate_names:
            if name in self.commit_history_cache:
                commits = self.commit_history_cache[name]
                print(f"   {name}: {len(commits)} commits in history")
                if commits:
                    sample_commit = commits[0]
                    files = sample_commit.get("files", [])
                    print(f"      Sample commit files: {[f.get('filename', '') for f in files[:3]]}")
            else:
                print(f"   {name}: NOT in commit_history_cache!")

        print(f"\n🔍 DEBUG: PR files being compared:")
        for f in pr_file_paths[:10]:
            print(f"   - {f}")
        ai_rankings = calculate_match_scores(
            pr_analysis=analysis,
            rag_roles=rag_roles,
            candidates=preliminary_candidates,
            pr_file_paths=pr_file_paths,
            repo=f"{self.owner}/{self.repo}",
            cache=self._profile_cache,
            prioritize_recent=prioritize_recent_activity
        )
        ai_by_name = {r.get("name", "").lower(): r for r in ai_rankings}

        final_candidates = []
        for c in preliminary_candidates:
            ai_result = ai_by_name.get(c["name"].lower(), {})
            ai_score = float(ai_result.get("confidence_score", 0)) / 100.0
            final_score = ai_result.get("confidence_score", 0)
            
            reasons = c.get("reasons", [])
            if not reasons:
                if c.get("required_reviewer"):
                    reasons.append("required_reviewer")
                if c.get("skill_score", 0) >= 0.5:
                    reasons.append("strong_skill_match")
                if prioritize_recent_activity and c.get("recency_score", 0) >= 0.5:
                    reasons.append("recent_activity_priority")

            final_candidates.append({
                "name": c["name"],
                "confidence_score": final_score,
                "justification": ai_result.get("justification", "Tversky-based scoring with AI enhancement."),
                "reasons": reasons,
                "required_reviewer": c.get("required_reviewer", False),
                "score_breakdown": ai_result.get("score_breakdown", {
                    "skill_score": c.get("skill_score", 0),
                    "recency_score": c.get("recency_score", 0),
                    "preliminary_score": c.get("prelim_score", 0),
                    "ai_score": round(ai_score, 4),
                }),
            })

        final_candidates.sort(key=lambda x: x["confidence_score"], reverse=True)

        if required_only_mode:
            recommended = final_candidates[:top_k]
        else:
            recommended = [
                c for c in final_candidates
                if c["name"].lower() not in required_set
            ][:top_k]

        return {
            "recommended_reviewers": recommended,
        }


if __name__ == "__main__":
    TARGET_OWNER = "huggingface"
    TARGET_REPO = "transformers"
    PR_NUMBER = 44935

    engine = ReviewerRecommender(TARGET_OWNER, TARGET_REPO)
    
    print("\n" + "═"*90)
    print("  SMART CACHE-AWARE INITIALIZATION")
    print("═"*90)
    
    # Smart initialization: skills from cache, commits from GitHub
    used_cache = engine.initialize_with_cache_check(
        required_developers=None,
        max_developers=2,
        max_commits=50,
        commits_per_reviewer=30
    )
    
    if used_cache:
        print("✅ Using cached skills - ZERO LLM calls made!")
    else:
        print("⚠️ Needed to process new developers with LLM")
    
    real_pr = fetch_real_pr_data(TARGET_OWNER, TARGET_REPO, PR_NUMBER)

    if real_pr:
        options = {
            "top_k": 10,
            "prioritize_recent_activity": True,
        }

        print(f"\n🚀 Ranking {len(engine.history_profiles)} developers...")
        run_output = engine.recommend_v2(real_pr, required_reviewers=[], options=options)
        results = run_output.get("recommended_reviewers", [])
        
        print("\n" + "═"*90)
        print(f"  TOP RECOMMENDATIONS from {len(engine.history_profiles)} developers")
        print("═"*90)
        print(f"{'RANK':<5} | {'DEVELOPER':<22} | {'SCORE':<8} | {'TVERSKY':<8} | {'AI':<8} | {'RECENCY':<8}")
        print("─"*90)

        for i, r in enumerate(results[:10], 1):
            breakdown = r.get('score_breakdown', {})
            tv_score = breakdown.get('tversky_score', 0)
            ai_score = breakdown.get('ai_score', 0)
            rec_score = breakdown.get('recency_score', 0)
            print(f" #{i:<4} | {r['name']:<22} | {r['confidence_score']:<8} | {tv_score:<8.2f} | {ai_score:<8.2f} | {rec_score:<8.2f}")
        
        print("═"*90)
        
        if results:
            best = results[0]
            print("\n" + "🏆" * 30)
            print(f"                    BEST MATCH: {best['name']}")
            print("🏆" * 30)
            
            print(f"\n📊 CONFIDENCE SCORE: {best['confidence_score']}/100")
            print(f"📝 JUSTIFICATION: {best['justification']}")
            
            print(f"\n📈 SCORE BREAKDOWN:")
            breakdown = best.get('score_breakdown', {})
            print(f"   ├─ Tversky Similarity:  {breakdown.get('tversky_score', 0):.3f}")
            print(f"   ├─ AI Score:            {breakdown.get('ai_score', 0):.3f}")
            print(f"   ├─ Recency Score:       {breakdown.get('recency_score', 0):.3f}")
            print(f"   ├─ Tenure Score:        {breakdown.get('tenure_score', 0):.3f}")
            print(f"   └─ Composite Score:     {breakdown.get('composite', 0):.3f}")
            
            print(f"\n⚙️ WEIGHTS USED:")
            weights = breakdown.get('weights', {})
            for weight_name, weight_value in weights.items():
                print(f"   ├─ {weight_name.capitalize()}: {weight_value}")
            
            print(f"\n✅ REASONS:")
            for reason in best.get('reasons', []):
                print(f"   • {reason.replace('_', ' ').title()}")
            
            print("\n" + "🏆" * 30)
            
            if len(results) > 1:
                print("\n📋 RUNNER-UPS:")
                for i, r in enumerate(results[1:3], 2):
                    print(f"   #{i}: {r['name']} - {r['confidence_score']}/100")
                    print(f"       {r['justification'][:80]}...")
        else:
            print("\n⚠️ No recommendations found")