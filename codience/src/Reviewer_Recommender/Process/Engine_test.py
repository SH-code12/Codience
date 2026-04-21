import os
import requests
from datetime import datetime, timezone
from typing import Any, Dict, List
from dotenv import load_dotenv
from codience.src.Reviewer_Recommender.Process.analysis_PR import extract_pr_skills

# Import your history logic
from codience.src.Reviewer_Recommender.Process.Reviewer_Engine_Helper import fetch_commits, map_commits_to_skills

# Import AI Agents
from codience.src.Reviewer_Recommender.Process.jira_agent import analyze_jira_context
from codience.src.Reviewer_Recommender.Process.scorer_agent import calculate_match_scores
from codience.src.Reviewer_Recommender.Data.searching_into_vectordb import search_vector_db

load_dotenv()

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
        # Cap at 30 files to avoid excessive API calls
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
        self.contributor_stats = {}
        self.repo_contributors = set()

    def initialize_system(self, max_commits=1000, max_llm_calls=40):
        print(f"🚀 Building Knowledge Base from last {max_commits} commits...")
        self.repo_contributors = fetch_repo_contributors(self.owner, self.repo)
        commits = fetch_commits(self.owner, self.repo, limit=max_commits)
        self.indexed_commits = commits
        self.contributor_stats = self._build_contributor_stats(commits)
        self.history_profiles = map_commits_to_skills(commits, max_llm_calls=max_llm_calls)

        # Keep contributors visible in the candidate pool even if skill extraction failed.
        for author in self.contributor_stats:
            self.history_profiles.setdefault(author, set())

        print(f"✅ Indexed {len(self.history_profiles)} developers.")

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
            if not isinstance(reviewer, str):
                continue
            clean_name = reviewer.strip()
            if not clean_name:
                continue
            key = clean_name.lower()
            if key not in required_map:
                required_map[key] = clean_name
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

        valid = []
        observed_contributors = set(self.history_profiles.keys()) | set(self.contributor_stats.keys())
        known_contributors = set(self.repo_contributors) | observed_contributors
        contributor_name_map = {name.lower(): name for name in known_contributors}
        for required_name in required_map.values():
            resolved = contributor_name_map.get(required_name.lower())
            if resolved:
                valid.append(resolved)

        return valid

    def recommend(self, pr_data):
        v2_result = self.recommend_v2(pr_data, required_reviewers=[], options={})
        return v2_result.get("recommended_reviewers", [])

    def recommend_v2(self, pr_data, required_reviewers=None, options=None):
        options = options or {}
        # top_k controls how many non-required reviewers are returned in the final recommendation list.
        raw_top_k = options.get("top_k")
        top_k = self.DEFAULT_TOP_K if raw_top_k is None else max(1, min(20, int(raw_top_k)))
        # When false, recency is treated equally for all contributors.
        raw_prioritize = options.get("prioritize_recent_activity")
        if raw_prioritize is None:
            prioritize_recent_activity = self.DEFAULT_PRIORITIZE_RECENT_ACTIVITY
        else:
            prioritize_recent_activity = bool(raw_prioritize)
        # Number of most recent commits considered per reviewer for activity signals.
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

        # Backfill history only for valid required contributors.
        self._ensure_required_reviewers_history(valid_required_contributors, commits_per_reviewer)

        # Recompute dynamic stats after adding required-reviewer history.
        limited_commits = self._limit_commits_per_reviewer(self.indexed_commits, commits_per_reviewer)
        dynamic_stats = self._build_contributor_stats(limited_commits)

        # 1. PR Analyzer Agent
        analysis = extract_pr_skills(pr_data)
        required_languages = {lang.strip().title() for lang in analysis.get('detected_languages', [])}
        
        if "C#" in required_languages:
            required_languages.remove("C#")
            required_languages.add(".NET")

        # 2. Vector DB RAG Search
        rag_query = analysis.get('rag_query', '') or ', '.join(required_languages)
        try:
            rag_roles = search_vector_db(rag_query, k=10) if rag_query else []
        except Exception as e:
            print(f"⚠️ Vector DB Search Failed: {e}")
            rag_roles = []

        # 3. Preliminary candidate scoring with optional recency prioritization.
        observed_contributors = set(self.history_profiles.keys()) | set(dynamic_stats.keys())
        repo_contributors = set(self.repo_contributors)

        if required_only_mode:
            # Strict required mode: evaluate only required reviewers that are valid repo contributors.
            candidate_names = set(valid_required_contributors)
        else:
            # No required list provided: analyze all contributors in repo, never external users.
            candidate_names = set(observed_contributors)
            if repo_contributors:
                candidate_names = {name for name in candidate_names if name in repo_contributors}

        preliminary_candidates = []
        for name in candidate_names:
            dev_skills = set(self.history_profiles.get(name, set()))
            matched_skills = required_languages.intersection(dev_skills) if required_languages else set()
            skill_score = len(matched_skills) / max(len(required_languages), 1) if required_languages else (1.0 if dev_skills else 0.0)

            stat = dynamic_stats.get(name, self.contributor_stats.get(name, {}))
            recency_score = stat.get("recency_score", 0.0)
            required_flag = name.lower() in required_set

            base_composite = skill_score
            if prioritize_recent_activity:
                # Fixed blend keeps API simple while still favoring active contributors.
                base_composite = (0.55 * skill_score) + (0.45 * recency_score)
            if required_flag:
                base_composite = min(1.0, base_composite + 0.10)

            preliminary_candidates.append({
                "name": name,
                "commit_skills": sorted(list(dev_skills)),
                "matched_skills": list(matched_skills),
                "skill_score": round(skill_score, 4),
                "recency_score": recency_score,
                "required_reviewer": required_flag,
                "prelim_score": round(base_composite, 4),
                "commit_count": stat.get("commit_count", 0),
                "tenure_days": stat.get("tenure_days", 365),
            })
            
        # By default, analyze all candidates and only apply top_k at final response slicing.
        preliminary_candidates = sorted(preliminary_candidates, key=lambda x: x['prelim_score'], reverse=True)

        # 4. Jira Analyzer Agent (Enrich candidates)
        for c in preliminary_candidates:
            print(f"🔄 Analyzing Jira Context for {c['name']}...")
            c["jira_context"] = analyze_jira_context(c["name"])

        # 5. Scorer Matchmaker Agent (AI explanation + confidence)
        print("🧠 Calculating AI Confidence Scores...")
        ai_rankings = calculate_match_scores(analysis, rag_roles, preliminary_candidates)
        ai_by_name = {r.get("name", "").lower(): r for r in ai_rankings}

        final_candidates = []
        for c in preliminary_candidates:
            ai_result = ai_by_name.get(c["name"].lower(), {})
            ai_score = float(ai_result.get("confidence_score", 0)) / 100.0
            final_score = int(round(100 * ((0.65 * c["prelim_score"]) + (0.35 * ai_score))))

            reasons = []
            if c.get("required_reviewer"):
                reasons.append("required_reviewer")
            if c.get("skill_score", 0) >= 0.5:
                reasons.append("strong_skill_match")
            if prioritize_recent_activity and c.get("recency_score", 0) >= 0.5:
                reasons.append("recent_activity_priority")

            final_candidates.append({
                "name": c["name"],
                "confidence_score": max(0, min(100, final_score)),
                "justification": ai_result.get("justification", "Composite scoring based on skills and recent contributor activity."),
                "reasons": reasons,
                "required_reviewer": c.get("required_reviewer", False),
                "score_breakdown": {
                    "skill_score": c.get("skill_score", 0),
                    "recency_score": c.get("recency_score", 0),
                    "preliminary_score": c.get("prelim_score", 0),
                    "ai_score": round(ai_score, 4),
                    "prioritize_recent_activity": prioritize_recent_activity,
                    "commits_considered_per_reviewer": commits_per_reviewer,
                },
            })

        final_candidates.sort(key=lambda x: x["confidence_score"], reverse=True)

        if required_only_mode:
            # In required-only mode, return ranked required reviewers directly.
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
    # Test on a repo that uses your skills (Java/SQL/Web)
    # https://api.github.com/repos/huggingface/transformers # 44935
    # https://api.github.com/repos/spring-petclinic/spring-framework-petclinic # 249
    TARGET_OWNER = "huggingface"
    TARGET_REPO = "transformers"
    PR_NUMBER = 44935 # Example PR number
    MAX_COMMITS = int(os.getenv("ENGINE_MAX_COMMITS", "1000"))
    MAX_LLM_CALLS = int(os.getenv("ENGINE_MAX_LLM_CALLS", "30"))

    engine = ReviewerRecommender(TARGET_OWNER, TARGET_REPO)
    engine.initialize_system(max_commits=MAX_COMMITS, max_llm_calls=MAX_LLM_CALLS)

    real_pr = fetch_real_pr_data(TARGET_OWNER, TARGET_REPO, PR_NUMBER)

    if real_pr:
        run_output = engine.recommend_v2(real_pr, required_reviewers=[], options={"top_k": 5})
        results = run_output.get("recommended_reviewers", [])
        
        print("\n" + "═"*90)
        print(f"  ACCURACY-MATCH REPORT: {TARGET_REPO}")
        print("═"*90)
        print(f"{'RANK':<5} | {'DEVELOPER':<18} | {'CONF SCORE':<10} | {'JUSTIFICATION'}")
        print("─"*90)

        for i, r in enumerate(results):
            icon = "⭐" if i == 0 else "  "
            conf_score = f"{r.get('confidence_score', 0)}/100"
            justif = r.get('justification', '')[:40] + "..." if len(r.get('justification', '')) > 40 else r.get('justification', '')
            
            print(f"{icon} #{i+1:<2} | {r['name']:<18} | {conf_score:<10} | {justif}")
        
        print("═"*90)
        if results and results[0].get('confidence_score', 0) > 0:
            print(f"🏆 BEST MATCH: {results[0]['name']}")
            print(f"   Reason: {results[0].get('justification', 'N/A')}")
        else:
            print("⚠️ No strong matches found in recent history.")
        print("═"*90)