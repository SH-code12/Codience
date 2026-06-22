# Fast API for reviewer recommendation
import os

from typing import Optional, Any
from fastapi import FastAPI
# pyrefly: ignore [missing-import]

from codience.src.models import (
    RecommendReviewersRequest,
    TicketListRequest,
    CommitHistoryRequest,
    ReviewerMatchRequest,
    OrchestratorRequest,
    ReviewerResponse,
)
from codience.src.helpers import (
    get_pr_data_or_raise,
    format_reviewer_results,
    _build_engine,
    _build_engine_for_required,
    _normalize_reviewers,
    get_composite_recommendations,
    _profile_single_user,
)
from codience.src.Reviewer_Recommender.PRNew.Reviewer_Engine import ReviewerRecommender
from codience.src.Reviewer_Recommender.PRNew.jira_agent import analyze_jira_tickets
from codience.src.Reviewer_Recommender.PRNew.commit_history_utils import map_commits_to_skills

app = FastAPI(title="Codience Reviewer Recommender API")

@app.post("/api/recommend-reviewers", response_model=dict[str, list[ReviewerResponse]])
async def recommend_reviewers(request: RecommendReviewersRequest):
    normalized_required = _normalize_reviewers(request.required_reviewers)
    options = request.options.model_dump(exclude_none=True) if request.options else {}
    
    # Bound options 
    if "top_k" in options:
        options["top_k"] = max(1, min(20, options["top_k"]))

    commits_per_reviewer = ReviewerRecommender.DEFAULT_COMMITS_PER_REVIEWER

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
    result = engine.recommend_v2(
        pr_data, 
        required_reviewers=normalized_required, 
        options=options,
        jira_token=request.jira_token,
        jira_cloud_id=request.jira_cloud_id,
        jira_project_key=request.jira_project_key
    )

    return {"recommended_reviewers": format_reviewer_results(result.get("recommended_reviewers", []))}


@app.post("/api/analyze/jira-tickets")
async def api_analyze_jira_tickets(request: TicketListRequest):
    result = analyze_jira_tickets(request.username, request.tickets)
    return result

@app.post("/api/analyze/commit-history")
async def api_analyze_commit_history(request: CommitHistoryRequest):
    skills_set = map_commits_to_skills(request.commits, repo="unknown/unknown", specific_authors=[request.author]).get(request.author, set())
    skills = list(skills_set)
    return {"skills": skills}

# get_composite_recommendations moved to codience.src.helpers


@app.post("/api/recommend/reviewer", response_model=dict[str, list[ReviewerResponse]])
async def api_recommend_reviewer(request: ReviewerMatchRequest):
    candidates = [c.model_dump() for c in request.candidates]
    results = get_composite_recommendations(request.pr_data, candidates, request.options)
    return {"recommended_reviewers": format_reviewer_results(results, limit=len(results))}


# _profile_single_user moved to codience.src.helpers


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
