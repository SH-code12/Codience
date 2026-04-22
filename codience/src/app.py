# Fast API for reviewer recommendation
import os
from typing import Optional, Any
from fastapi import FastAPI
from pydantic import BaseModel, Field
from codience.src.Reviewer_Recommender.Process.Engine_test import ReviewerRecommender, fetch_real_pr_data

app = FastAPI()


class ReviewerRequest(BaseModel):
    # GitHub repository owner or organization.
    owner: str
    # GitHub repository name.
    repo: str
    # Pull request number in the target repository.
    pr_number: int


class RankingOptions(BaseModel):
    # Maximum number of non-required recommendations returned in recommended_reviewers.
    top_k: Optional[int] = Field(default=None, description="Optional override. Default is 5 (allowed range: 1-20).")
    # Toggle recency prioritization in ranking.
    prioritize_recent_activity: Optional[bool] = Field(
        default=None,
        description="Optional override. Default is true; false treats recency equally.",
    )
    # Number of most recent commits considered per reviewer for activity-based ranking signals.
    commits_per_reviewer: Optional[int] = Field(
        default=None,
        description="Optional override. Default is 50 recent commits per reviewer (allowed range: 1-100).",
    )


class ReviewerRequestV2(BaseModel):
    # GitHub repository owner or organization.
    owner: str
    # GitHub repository name.
    repo: str
    # Pull request number in the target repository.
    pr_number: int
    # Frontend-provided must-consider reviewers. Can be usernames (str) or entities (dict).
    required_reviewers: list[Any] = Field(default_factory=list)
    # Optional tuning knobs. Omitted fields use server-side defaults.
    options: Optional[RankingOptions] = None


def _build_engine(owner, repo, min_commits=None):
    """Full init: indexes all repo contributors. Used when no required reviewers are provided."""
    engine = ReviewerRecommender(owner, repo)
    max_commits = int(os.getenv("ENGINE_MAX_COMMITS", "1000"))
    if min_commits is not None:
        max_commits = max(max_commits, int(min_commits))
    max_llm_calls = int(os.getenv("ENGINE_MAX_LLM_CALLS", "30"))
    engine.initialize_system(max_commits=max_commits, max_llm_calls=max_llm_calls)
    return engine


def _build_engine_for_required(owner, repo, required_reviewers, commits_per_reviewer=50):
    """Lean init: only fetches history for the specified required reviewers."""
    engine = ReviewerRecommender(owner, repo)
    max_llm_calls = int(os.getenv("ENGINE_MAX_LLM_CALLS", "20"))
    engine.initialize_for_required_only(
        required_reviewers=required_reviewers,
        commits_per_reviewer=commits_per_reviewer,
        max_llm_calls=max_llm_calls,
    )
    return engine


@app.post("/api/recommend")
async def recommend(request: ReviewerRequest):
    engine = _build_engine(request.owner, request.repo)

    real_pr = fetch_real_pr_data(request.owner, request.repo, request.pr_number)
    if not real_pr:
        return {"error": "Failed to fetch PR data."}
    
    results = engine.recommend(real_pr)

    formatted_results = []
    for res in results[:5]:  # Return top 5 maximum
        formatted_results.append({
            "name": res.get("name"),
            "confidence_score": res.get("confidence_score", 0),
            "justification": res.get("justification", ""),
        })
    return {"reviewers": formatted_results}


@app.post("/api/recommend/v2")
async def recommend_v2(request: ReviewerRequestV2):
    normalized_required = []
    seen = set()
    # Normalize and dedupe required reviewers.
    for reviewer in request.required_reviewers:
        username = None
        if isinstance(reviewer, str):
            username = reviewer.strip()
        elif isinstance(reviewer, dict):
            username = (reviewer.get("username") or reviewer.get("login") or "").strip()
        
        if not username:
            continue
            
        lower = username.lower()
        if lower in seen:
            continue
        seen.add(lower)
        # We pass the original object (str or dict) to the engine's internal normalization
        normalized_required.append(reviewer)

    options = request.options.model_dump(exclude_none=True) if request.options else {}
    # Keep top_k bounded for API safety and predictable runtime when provided.
    if "top_k" in options:
        if options["top_k"] < 1:
            options["top_k"] = 1
        if options["top_k"] > 20:
            options["top_k"] = 20
    # Bound commits_per_reviewer for predictable runtime when provided.
    if "commits_per_reviewer" in options:
        if options["commits_per_reviewer"] < 1:
            options["commits_per_reviewer"] = 1
        if options["commits_per_reviewer"] > 100:
            options["commits_per_reviewer"] = 100

    commits_per_reviewer = options.get("commits_per_reviewer", ReviewerRecommender.DEFAULT_COMMITS_PER_REVIEWER)

    if normalized_required:
        # Fast path: only analyze the explicitly listed reviewers.
        engine = _build_engine_for_required(
            request.owner, request.repo,
            required_reviewers=normalized_required,
            commits_per_reviewer=commits_per_reviewer,
        )
    else:
        # Full path: index all repo contributors.
        top_k = options.get("top_k", ReviewerRecommender.DEFAULT_TOP_K)
        min_commits = int(commits_per_reviewer) * max(int(top_k), 1)
        engine = _build_engine(request.owner, request.repo, min_commits=min_commits)

    real_pr = fetch_real_pr_data(request.owner, request.repo, request.pr_number)
    if not real_pr:
        return {"error": "Failed to fetch PR data."}

    result = engine.recommend_v2(
        real_pr,
        required_reviewers=normalized_required,
        options=options,
    )

    # Keep v2 payload lean for frontend consumption.
    slim_recommended = []
    for reviewer in result.get("recommended_reviewers", []):
        slim_recommended.append(
            {
                "name": reviewer.get("name"),
                "confidence_score": reviewer.get("confidence_score", 0),
                "justification": reviewer.get("justification", ""),
            }
        )

    return {"recommended_reviewers": slim_recommended}
