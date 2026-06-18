"""
main.py - FastAPI Application for PR Business Impact Ranking
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import asyncio
import os
from datetime import datetime

# Import your existing modules
from models import PRPayload, RankBatchRequest, RankedPRList, PRScoreResult
from coreRanking import PRRankingEngine
from pr_fetcher_with_dotnet import PRFetcherWithDotNet
from dotnet_jira_client import get_dotnet_client, fetch_authenticated_github_email
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="PR Business Impact Ranking API",
    description="API for ranking pull requests by business impact using local AI models",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
ranking_engine = PRRankingEngine()
pr_fetcher = PRFetcherWithDotNet()
dotnet_client = get_dotnet_client()

# ---------------------------------------------------------------------------
# Health Check Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "PR Business Impact Ranking API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/api/rank": "Rank PRs from provided data",
            "/api/rank/repo/{owner}/{repo}": "Fetch and rank PRs from GitHub repo",
            "/api/rank/pr/{owner}/{repo}/{pr_number}": "Rank a single PR",
            "/api/github/status": "Check GitHub connection status"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "github": "✅" if os.getenv("GITHUB_TOKEN") else "❌",
            "jira": "✅" if os.getenv("JIRA_API_TOKEN") else "❌",
            "ollama": await _check_ollama(),
        }
    }

async def _check_ollama() -> str:
    """Check if Ollama is running"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://127.0.0.1:11434/api/tags")
            if response.status_code == 200:
                return "✅"
            return "⚠️"
    except:
        return "❌"


# ---------------------------------------------------------------------------
# GitHub Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/github/status")
async def github_status():
    """Check GitHub connection status"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {
            "status": "not_configured",
            "message": "GITHUB_TOKEN not set in environment"
        }
    
    try:
        import requests
        headers = {"Authorization": f"token {token}"}
        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        
        if response.status_code == 200:
            user = response.json()
            return {
                "status": "connected",
                "user": user.get("login"),
                "name": user.get("name"),
                "email": fetch_authenticated_github_email()
            }
        else:
            return {
                "status": "error",
                "code": response.status_code,
                "message": response.text[:100]
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ---------------------------------------------------------------------------
# Ranking Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/rank", response_model=RankedPRList)
async def rank_prs(request: RankBatchRequest):
    """
    Rank a batch of PRs by business impact.
    
    Request body should contain a list of PRPayload objects.
    Returns sorted list with scores and impact tiers.
    """
    try:
        # Get user email for context
        user_email = fetch_authenticated_github_email()
        if not user_email:
            user_email = "unknown@domain.internal"
        
        # Score PRs with context
        scored_results = []
        for pr in request.prs:
            result = await ranking_engine.score_single_pr(pr, reporter_email=user_email)
            scored_results.append(result)
        
        # Sort by score
        ranked = sorted(scored_results, key=lambda x: x.weighted_score, reverse=True)
        
        return RankedPRList(
            total=len(ranked),
            ranked=ranked,
            high_count=sum(1 for r in ranked if r.tier.value == "high"),
            medium_count=sum(1 for r in ranked if r.tier.value == "medium"),
            low_count=sum(1 for r in ranked if r.tier.value == "low")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rank/repo/{owner}/{repo}")
async def rank_repo_prs(
    owner: str,
    repo: str,
    max_prs: int = 10,
    background_tasks: BackgroundTasks = None
):
    """
    Fetch PRs from a GitHub repository and rank them by business impact.
    
    - owner: GitHub repository owner
    - repo: GitHub repository name
    - max_prs: Maximum number of PRs to fetch (default: 20)
    """
    try:
        repo_name = f"{owner}/{repo}"
        
        # Get user email for context
        user_email = fetch_authenticated_github_email()
        if not user_email:
            user_email = "unknown@domain.internal"
        
        # Fetch PRs from GitHub
        prs = pr_fetcher.fetch_open_prs(repo_name, max_prs=max_prs, user_email=user_email)
        
        if not prs:
            return {
                "status": "no_prs_found",
                "message": f"No open PRs found in {repo_name}",
                "ranked": [],
                "total": 0
            }
        
        # Score PRs
        scored_results = []
        for pr in prs:
            result = await ranking_engine.score_single_pr(pr, reporter_email=user_email)
            scored_results.append(result)
        
        # Sort by score
        ranked = sorted(scored_results, key=lambda x: x.weighted_score, reverse=True)
        
        # Add background task for caching (optional)
        if background_tasks:
            background_tasks.add_task(_cache_results, ranked, repo_name)
        
        return RankedPRList(
            total=len(ranked),
            ranked=ranked,
            high_count=sum(1 for r in ranked if r.tier.value == "high"),
            medium_count=sum(1 for r in ranked if r.tier.value == "medium"),
            low_count=sum(1 for r in ranked if r.tier.value == "low")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# Add this import at the top if not already present
from typing import Optional
import re

# Add this endpoint after your existing ranking endpoints
@app.get("/api/rank/pr/{owner}/{repo}/{pr_number}")
async def rank_single_pr_by_id(owner: str, repo: str, pr_number: int):
    """
    Fetch and evaluate a single Pull Request by its explicit number.
    Applies live .NET Jira context maps, runs local LLM analysis summaries, 
    and returns a clean business-focused metric payload.
    """
    try:
        repo_name = f"{owner}/{repo}"
        user_email = fetch_authenticated_github_email() or "unknown@domain.internal"
        
        # Pull single targeted payload structure via indirect batch limit logic
        prs = pr_fetcher.fetch_open_prs(repo_name, max_prs=50, user_email=user_email)
        target_pr = next((p for p in prs if p.pr_number == pr_number), None)
        
        # Fallback manual retrieval loop if state isn't visible via open collection
        if not target_pr:
            if pr_fetcher.github:
                raw_pr_data = pr_fetcher.github.get_pull_request(owner, repo, pr_number)
                payload = pr_fetcher._github_pr_to_dict(raw_pr_data, owner, repo)
                enriched_payload = pr_fetcher.pr_enricher.enrich_pr_with_jira(payload, fallback_email=user_email)
                target_pr = pr_fetcher._dict_to_pr_payload(enriched_payload, raw_pr_data, owner, repo)
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub Client uninitialized.")
                
        if not target_pr:
            raise HTTPException(status_code=404, detail=f"PR #{pr_number} could not be resolved from {repo_name}")
            
        # Execute calculation cycle pipeline directly 
        score_res: PRScoreResult = await ranking_engine.score_single_pr(target_pr, reporter_email=user_email)
        
        # Structure payload to match custom frontend tracking contract precisely
        bd = score_res.score_breakdown or {}
        return {
            "pr_number": score_res.pr_number,
            "pr_title": score_res.pr_title,
            "weighted_score": score_res.weighted_score,
            "tier": score_res.tier.value,
            "should_block_merge": score_res.should_block_merge,
            "ai_summary": score_res.llm_semantic.business_summary if score_res.llm_semantic else "No summary available.",
            "score_breakdown": {
                "blast_radius": round(score_res.blast_radius.score, 4) if score_res.blast_radius else 0.0,
                "user_exposure": round(score_res.user_exposure.score, 4) if score_res.user_exposure else 0.0,
                "deadline": round(score_res.deadline.score, 4) if score_res.deadline else 0.0,
                "business_impact": round(score_res.weighted_score, 4),
                "formula_score": round(bd.get("formula_score", bd.get("business_impact", 0.0) / 100.0), 6),
                "local_model_score": round(score_res.llm_semantic.raw_score, 4) if score_res.llm_semantic else 0.0
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed single PR rank computation process: {str(e)}")
# ---------------------------------------------------------------------------
# Utility Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/repo/{owner}/{repo}")
async def get_repo_prs(owner: str, repo: str, max_prs: int = 20):
    """
    Fetch PRs from a GitHub repository without ranking.
    Useful for debugging.
    """
    try:
        repo_name = f"{owner}/{repo}"
        user_email = fetch_authenticated_github_email()
        prs = pr_fetcher.fetch_open_prs(repo_name, max_prs=max_prs, user_email=user_email)
        
        return {
            "total": len(prs),
            "prs": [
                {
                    "number": p.pr_number,
                    "title": p.pr_title,
                    "author": p.repo_owner,
                    "jira_tickets": [t.key for t in p.linked_jira_tickets],
                    "changed_files": len(p.changed_files)
                }
                for p in prs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/tickets/{assignee}")
async def get_jira_tickets(assignee: str):
    """
    Get Jira tickets assigned to a user.
    
    - assignee: Jira username or email
    """
    try:
        tickets = dotnet_client.get_assigned_tickets(assignee_name=assignee)
        return {
            "total": len(tickets),
            "tickets": tickets[:50]  # Limit to 50 for performance
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Background Tasks
# ---------------------------------------------------------------------------

async def _cache_results(ranked_results: List[PRScoreResult], repo_name: str):
    """Cache ranking results (optional)"""
    import json
    from pathlib import Path
    
    cache_file = Path(__file__).parent / f"cache_{repo_name.replace('/', '_')}.json"
    try:
        data = [
            {
                "pr_number": r.pr_number,
                "weighted_score": r.weighted_score,
                "tier": r.tier.value,
                "timestamp": datetime.now().isoformat()
            }
            for r in ranked_results
        ]
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not cache results: {e}")

# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
    )

# ---------------------------------------------------------------------------
# Start the server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("🚀 Starting PR Business Impact Ranking API")
    print("=" * 80)
    print(f"\n📍 API URL: http://localhost:8001")
    print(f"📚 API Docs: http://localhost:8001/docs")
    print(f"🔍 Health: http://localhost:8001/health")
    print("\nPress Ctrl+C to stop\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )