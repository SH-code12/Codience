# Fast API for reviewer recommendation
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from typing import Optional, Any
from fastapi import FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from codience.src.Reviewer_Recommender.Process.Engine_test import ReviewerRecommender, fetch_real_pr_data
from codience.src.Reviewer_Recommender.Process.jira_agent import analyze_jira_tickets, fetch_jira_tickets
from codience.src.Reviewer_Recommender.Process.Reviewer_Engine_Helper import analyze_user_commit_history
from codience.src.Reviewer_Recommender.Process.analysis_PR import extract_pr_skills
from codience.src.Reviewer_Recommender.Data.searching_into_vectordb import search_vector_db
from codience.src.Reviewer_Recommender.Process.scorer_agent import calculate_match_scores

app = FastAPI(title="Codience Reviewer Recommender API")


# --- Models ------------------------------------------------------------------

class BaseRepoRequest(BaseModel):
    owner: str = Field(..., description="GitHub repository owner or organization.")
    repo: str = Field(..., description="GitHub repository name.")
    pr_number: int = Field(..., description="Pull request number.")


class RankingOptions(BaseModel):
    top_k: Optional[int] = Field(default=None, description="Max recommendations (1-20). Default 5.")
    prioritize_recent_activity: Optional[bool] = Field(default=None, description="Toggle recency prioritization.")
    commits_per_reviewer: Optional[int] = Field(default=None, description="Recent commits considered (1-100). Default 50.")


class ReviewerRequest(BaseRepoRequest):
    pass


class ReviewerRequestV2(BaseRepoRequest):
    required_reviewers: list[Any] = Field(default_factory=list, description="Explicit reviewers to consider (strings or dicts).")
    options: Optional[RankingOptions] = None


class TicketListRequest(BaseModel):
    username: str
    tickets: list[Any]


class CommitHistoryRequest(BaseModel):
    author: str
    commits: list[Any]


class CandidateProfile(BaseModel):
    name: str
    jira_username: Optional[str] = None
    commit_skills: list[str] = []
    jira_context: dict = {}
    commit_count: int = 0
    tenure_days: int = 365
    recency_score: float = 0.0
    required_reviewer: bool = False
    raw_skills: list[str] = []
    prelim_score: float = 0.0


class ReviewerMatchRequest(BaseModel):
    pr_data: dict
    candidates: list[CandidateProfile]
    options: Optional[RankingOptions] = None


class OrchestratorUser(BaseModel):
    github_username: str
    jira_username: Optional[str] = None
    jira_token: Optional[str] = None
    jira_cloud_id: Optional[str] = None
    jira_project_key: Optional[str] = None
    raw_skills: list[str] = []


class OrchestratorRequest(BaseRepoRequest):
    users: list[OrchestratorUser]
    commits_per_user: Optional[int] = 50
    options: Optional[RankingOptions] = None


class ReviewerResponse(BaseModel):
    name: str
    confidence_score: int
    justification: str


# --- Helpers -----------------------------------------------------------------

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
    max_llm_calls = int(os.getenv("ENGINE_MAX_LLM_CALLS", "30"))
    engine.initialize_system(max_commits=max_commits, max_llm_calls=max_llm_calls)
    return engine


def _build_engine_for_required(owner: str, repo: str, required_reviewers: list, commits_per_reviewer: int = 50) -> ReviewerRecommender:
    """Lean init: only fetches history for the specified required reviewers."""
    engine = ReviewerRecommender(owner, repo)
    max_llm_calls = int(os.getenv("ENGINE_MAX_LLM_CALLS", "20"))
    engine.initialize_for_required_only(
        required_reviewers=required_reviewers,
        commits_per_reviewer=commits_per_reviewer,
        max_llm_calls=max_llm_calls,
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


@app.post("/api/recommend", response_model=dict[str, list[ReviewerResponse]])
async def recommend(request: ReviewerRequest):
    engine = _build_engine(request.owner, request.repo)
    pr_data = get_pr_data_or_raise(request.owner, request.repo, request.pr_number)
    
    results = engine.recommend(pr_data)
    return {"reviewers": format_reviewer_results(results)}


@app.post("/api/recommend/v2", response_model=dict[str, list[ReviewerResponse]])
async def recommend_v2(request: ReviewerRequestV2):
    normalized_required = _normalize_reviewers(request.required_reviewers)
    options = request.options.model_dump(exclude_none=True) if request.options else {}
    
    # Bound options
    if "top_k" in options:
        options["top_k"] = max(1, min(20, options["top_k"]))
    if "commits_per_reviewer" in options:
        options["commits_per_reviewer"] = max(1, min(100, options["commits_per_reviewer"]))

    commits_per_reviewer = options.get("commits_per_reviewer", ReviewerRecommender.DEFAULT_COMMITS_PER_REVIEWER)

    if normalized_required:
        engine = _build_engine_for_required(
            request.owner, request.repo,
            required_reviewers=normalized_required,
            commits_per_reviewer=commits_per_reviewer,
        )
    else:
        top_k = options.get("top_k", ReviewerRecommender.DEFAULT_TOP_K)
        min_commits = int(commits_per_reviewer) * max(int(top_k), 1)
        engine = _build_engine(request.owner, request.repo, min_commits=min_commits)

    pr_data = get_pr_data_or_raise(request.owner, request.repo, request.pr_number)
    result = engine.recommend_v2(pr_data, required_reviewers=normalized_required, options=options)

    return {"recommended_reviewers": format_reviewer_results(result.get("recommended_reviewers", []))}


@app.post("/api/analyze/jira-tickets")
async def api_analyze_jira_tickets(request: TicketListRequest):
    result = analyze_jira_tickets(request.username, request.tickets)
    return result

@app.post("/api/analyze/commit-history")
async def api_analyze_commit_history(request: CommitHistoryRequest):
    skills = analyze_user_commit_history(request.author, request.commits)
    return {"skills": skills}

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

    from codience.src.Reviewer_Recommender.Data.commit_diff_vectordb import search_similar_commits
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


@app.post("/api/recommend/reviewer", response_model=dict[str, list[ReviewerResponse]])
async def api_recommend_reviewer(request: ReviewerMatchRequest):
    candidates = [c.model_dump() for c in request.candidates]
    results = get_composite_recommendations(request.pr_data, candidates, request.options)
    return {"recommended_reviewers": format_reviewer_results(results, limit=len(results))}


def _profile_single_user(user: OrchestratorUser, engine: ReviewerRecommender, commits_per_user: int) -> dict:
    """Collects GitHub and Jira data for a single user to build their candidate profile."""
    github_username = user.github_username
    
    # 1. GitHub History
    author_commits = engine._fetch_commits_for_author(github_username, commits_per_user)
    commit_skills = analyze_user_commit_history(github_username, author_commits)
    
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


@app.post("/api/orchestrator", response_model=dict[str, list[ReviewerResponse]])
async def api_orchestrator(request: OrchestratorRequest):
    pr_data = get_pr_data_or_raise(request.owner, request.repo, request.pr_number)
    engine = ReviewerRecommender(request.owner, request.repo)
    commits_per_user = request.commits_per_user or 50

    # Profile all requested users
    candidates = [
        _profile_single_user(user, engine, commits_per_user) 
        for user in request.users
    ]

    # Calculate final rankings
    results = get_composite_recommendations(pr_data, candidates, request.options)
    return {"recommended_reviewers": format_reviewer_results(results, limit=len(results))}
