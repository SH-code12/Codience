import os
from typing import Optional, Any
from fastapi import HTTPException

# Models
from codience.src.models import (
    ReviewerResponse,
    RankingOptions,
    OrchestratorUser,
)

# External engine and agent imports
from codience.src.Reviewer_Recommender.PRNew.Reviewer_Engine import ReviewerRecommender, fetch_real_pr_data
from codience.src.Reviewer_Recommender.PRNew.jira_agent import analyze_jira_tickets, fetch_jira_tickets
from codience.src.Reviewer_Recommender.PRNew.commit_history_utils import fetch_commit_history_for_author, map_commits_to_skills
from codience.src.Reviewer_Recommender.PRNew.analysis_PR import extract_pr_skills
from codience.src.Reviewer_Recommender.Data.searching_into_vectordb import search_vector_db
from codience.src.Reviewer_Recommender.PRNew.scorer_agent import calculate_match_scores
from codience.src.Reviewer_Recommender.Data.commit_diff_vectordb import search_similar_commits


def get_pr_data_or_raise(owner: str, repo: str, pr_number: int) -> dict:
    """Centralized helper to fetch and validate PR data."""
    real_pr = fetch_real_pr_data(owner, repo, pr_number)
    if not real_pr:
        raise HTTPException(status_code=404, detail=f"Failed to fetch PR #{pr_number} data for {owner}/{repo}.")
    return real_pr


def format_reviewer_results(results: list[dict], limit: int = 5) -> list[ReviewerResponse]:
    """Uniformly formats internal reviewer dicts for API response."""
    formatted = []
    for res in results[:limit]:
        formatted.append(ReviewerResponse(
            name=res.get("name", "Unknown"),
            confidence_score=int(res.get("confidence_score", 0)),
            justification=res.get("justification", "")
        ))
    return formatted


def _build_engine(owner: str, repo: str, min_commits: Optional[int] = None) -> ReviewerRecommender:
    """Full init: indexes all repo contributors."""
    engine = ReviewerRecommender(owner, repo)
    max_commits = int(os.getenv("ENGINE_MAX_COMMITS", "1000"))
    if min_commits is not None:
        max_commits = max(max_commits, int(min_commits))
    engine.initialize_with_cache_check(max_developers=50, max_commits=max_commits)
    return engine


def _build_engine_for_required(owner: str, repo: str, required_reviewers: list, commits_per_reviewer: int = 50) -> ReviewerRecommender:
    """Lean init: only fetches history for the specified required reviewers."""
    engine = ReviewerRecommender(owner, repo)
    engine.initialize_with_cache_check(
        required_developers=required_reviewers,
        commits_per_reviewer=commits_per_reviewer,
        max_commits=500,
    )
    return engine


def _normalize_reviewers(reviewers: list[Any]) -> list[Any]:
    """Deduplicates and normalizes strings/dicts into a clean list of reviewer identifiers."""
    normalized = []
    seen = set()
    for r in reviewers:
        username = r.strip() if isinstance(r, str) else (r.get("username") or r.get("login") or "").strip()
        if username and username.lower() not in seen:
            seen.add(username.lower())
            normalized.append(r)
    return normalized


def get_composite_recommendations(pr_data: dict, candidates: list[dict], options: Optional[RankingOptions] = None) -> list[dict]:
    """
    Business logic for calculating composite scores based on AI analysis, 
    preliminary scores, and recency signals.
    """
    analysis = extract_pr_skills(pr_data)
    required_languages = {lang.strip().title() for lang in analysis.get('detected_languages', [])}
    if "C#" in required_languages:
        required_languages.remove("C#")
        required_languages.add(".NET")

    rag_query = analysis.get('rag_query', '') or ', '.join(required_languages)
    try:
        rag_roles = search_vector_db(rag_query, k=10) if rag_query else []
    except Exception as e:
        print(f"⚠️ Vector DB Search Failed: {e}")
        rag_roles = []

    pr_patch_text = "\n".join([f.get("patch", "") for f in pr_data.get("files", []) if f.get("patch")])
    rag_commits = []
    if pr_patch_text:
        try:
            rag_commits = search_similar_commits(pr_patch_text, k=15)
        except Exception as e:
            print(f"⚠️ Code Diff Vector DB Search Failed: {e}")

    author_rag_matches = {}
    for res in rag_commits:
        author = res.metadata.get("author")
        if author:
            author_rag_matches[author.lower()] = author_rag_matches.get(author.lower(), 0) + 1

    for c in candidates:
        rag_match_count = author_rag_matches.get(c["name"].lower(), 0)
        max_rag = max(author_rag_matches.values()) if author_rag_matches else 1
        rag_match_score = rag_match_count / max_rag if max_rag > 0 else 0.0
        
        c["prelim_score"] = (0.7 * c.get("prelim_score", 0)) + (0.3 * rag_match_score)
        
        matched_diffs = [res.page_content for res in rag_commits if res.metadata.get("author", "").lower() == c["name"].lower()]
        c["rag_code_matches"] = matched_diffs[:3]

    ai_rankings = calculate_match_scores(analysis, rag_roles, candidates)
    ai_by_name = {r.get("name", "").lower(): r for r in ai_rankings}

    final_candidates = []
    for c in candidates:
        ai_result = ai_by_name.get(c["name"].lower(), {})
        ai_score = float(ai_result.get("confidence_score", 0)) / 100.0
        
        # Scoring weights: 65% Preliminary (Commit/Jira), 35% AI Match (Matchmaker)
        final_score = int(round(100 * ((0.65 * c.get("prelim_score", 0)) + (0.35 * ai_score))))

        reasons = []
        if c.get("required_reviewer"):
            reasons.append("required_reviewer")
        if c.get("recency_score", 0) >= 0.5:
            reasons.append("recent_activity_priority")
            
        final_candidates.append({
            "name": c["name"],
            "confidence_score": max(0, min(100, final_score)),
            "justification": ai_result.get("justification", "Composite scoring based on skills and recent contributor activity."),
            "reasons": reasons,
            "required_reviewer": c.get("required_reviewer", False),
        })

    final_candidates.sort(key=lambda x: x["confidence_score"], reverse=True)
    return final_candidates


def _profile_single_user(user: OrchestratorUser, engine: ReviewerRecommender, commits_per_user: int) -> dict:
    """Collects GitHub and Jira data for a single user to build their candidate profile."""
    github_username = user.github_username
    
    # 1. GitHub History
    author_commits = fetch_commit_history_for_author(github_username, engine.owner, engine.repo, limit=commits_per_user)
    commit_skills_set = map_commits_to_skills(author_commits, repo=f"{engine.owner}/{engine.repo}", specific_authors=[github_username]).get(github_username, set())
    commit_skills = list(commit_skills_set)
    
    # 2. Jira Context
    tickets = fetch_jira_tickets(
        username=github_username, 
        jira_username=user.jira_username,
        token=user.jira_token,
        cloud_id=user.jira_cloud_id,
        project_key=user.jira_project_key
    )
    jira_context = analyze_jira_tickets(github_username, tickets)
    
    # 3. Stats & Scoring
    stats = engine._build_contributor_stats(author_commits).get(github_username, {})
    recency_score = stats.get("recency_score", 0.0)
    
    # Simple preliminary skill-match heuristic
    skill_score = 0.8 if commit_skills else 0.5
    prelim_score = (0.55 * skill_score) + (0.45 * recency_score)
    
    return {
        "name": github_username,
        "jira_username": user.jira_username,
        "commit_skills": commit_skills,
        "jira_context": jira_context,
        "commit_count": stats.get("commit_count", 0),
        "tenure_days": stats.get("tenure_days", 365),
        "recency_score": recency_score,
        "required_reviewer": True,
        "raw_skills": user.raw_skills,
        "prelim_score": prelim_score
    }
