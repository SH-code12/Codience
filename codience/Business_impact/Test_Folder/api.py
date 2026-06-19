"""
main.py - FastAPI Application for PR Business Impact Ranking
Features dynamic routing health checks mapping backend architectures explicitly.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
import os
import requests
from datetime import datetime

from models import RankBatchRequest, RankedPRList, PRScoreResult, PRPayload
from coreRanking import PRRankingEngine
from codience.Business_impact.Test_Folder.pr_dotnet import PRFetcherWithDotNet
from dotnet_jira_client import get_dotnet_client, fetch_authenticated_github_email
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="PR Business Impact Ranking API",
    description="Resilient API for ranking pull requests by business impact supporting direct .NET failovers",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ranking_engine = PRRankingEngine()
pr_fetcher = PRFetcherWithDotNet()
dotnet_client = get_dotnet_client()


@app.get("/")
async def root():
    return {
        "service": "PR Business Impact Ranking API (Resilient Mode)",
        "version": "1.0.0",
        "backend_proxy_target": os.getenv("DOTNET_BACKEND_URL", "http://localhost:5051")
    }


@app.get("/health")
async def health_check():
    # Dynamic health computation probing configurations directly
    is_dotnet_up = pr_fetcher.github.is_backend_online()
    has_local_token = bool(os.getenv("GITHUB_TOKEN"))
    
    return {
        "status": "healthy" if (is_dotnet_up or has_local_token) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "dotnet_backend_layer": "✅ ONLINE" if is_dotnet_up else "❌ OFFLINE (Falling back to native API)",
            "github_token_configured": "✅" if has_local_token else "❌",
            "ollama": await _check_ollama(),
        }
    }

async def _check_ollama() -> str:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get("http://127.0.0.1:11434/api/tags")
            return "✅" if response.status_code == 200 else "⚠️"
    except Exception:
        return "❌"


@app.get("/api/github/status")
async def github_status():
    """Checks configuration topologies safely."""
    token = os.getenv("GITHUB_TOKEN")
    is_backend_up = pr_fetcher.github.is_backend_online()
    
    if not token and not is_backend_up:
        return {
            "status": "disconnected",
            "message": "Neither direct GITHUB_TOKEN nor active local .NET Backend routers could be resolved."
        }
        
    return {
        "status": "operational",
        "routing_strategy": "DotNet Controller Gateway Proxy" if is_backend_up else "Direct GitHub REST API Fallback Client",
        "authenticated_email": fetch_authenticated_github_email() or "unknown@domain.internal"
    }


@app.get("/api/rank/repo/{owner}/{repo}")
async def rank_repo_prs(owner: str, repo: str, max_prs: int = 10, background_tasks: BackgroundTasks = None):
    try:
        repo_name = f"{owner}/{repo}"
        user_email = fetch_authenticated_github_email() or "unknown@domain.internal"
        
        # Pull records safely using resilient fallback wrapper logic
        prs = pr_fetcher.fetch_open_prs(repo_name, max_prs=max_prs, user_email=user_email)
        
        if not prs:
            return {"status": "no_prs_found", "message": f"No open PR data sets retrieved from {repo_name}", "ranked": [], "total": 0}
        
        scored_results = []
        for pr in prs:
            result = await ranking_engine.score_single_pr(pr, reporter_email=user_email)
            scored_results.append(result)
            
        ranked = sorted(scored_results, key=lambda x: x.weighted_score, reverse=True)
        
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
        raise HTTPException(status_code=500, detail=f"Ranking pipeline processing loop error: {str(e)}")


@app.get("/api/rank/pr/{owner}/{repo}/{pr_number}")
async def rank_single_pr_by_id(owner: str, repo: str, pr_number: int):
    try:
        repo_name = f"{owner}/{repo}"
        user_email = fetch_authenticated_github_email() or "unknown@domain.internal"
        
        # Leverage resilient fetch architecture logic to capture data
        prs = pr_fetcher.fetch_open_prs(repo_name, max_prs=50, user_email=user_email)
        target_pr = next((p for p in prs if p.pr_number == pr_number), None)
        
        # Explicit secondary direct extraction fallback strategy sequence
        if not target_pr:
            # Force target parsing manually utilizing internal model factories
            files = pr_fetcher.github.get_pr_files(owner, repo, pr_number)
            diff_str = pr_fetcher.github.get_pr_diff(owner, repo, pr_number)
            
            if not diff_str:
                diff_str = "\n".join([f"diff --git a/{f.get('filename')} b/{f.get('filename')}\n{f.get('patch','')}" for f in files[:20]])
                
            # Construct a raw mock payload base context record object map
            target_pr = PRPayload(
                pr_number=pr_number,
                pr_title=f"PR #{pr_number} Fallback Trace Profile",
                pr_body="Content context parsed via dynamic fallback trace pipelines.",
                repo_owner=owner,
                repo_name=repo,
                head_branch="unknown",
                base_branch="main",
                diff_excerpt=diff_str[:6000],
                changed_files=[f.get("filename") for f in files[:50] if f],
                github_labels=[],
                linked_jira_tickets=[]
            )
            
        score_res = await ranking_engine.score_single_pr(target_pr, reporter_email=user_email)
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
                "formula_score": round(bd.get("formula_score", 0.0), 6),
                "local_model_score": round(score_res.llm_semantic.raw_score, 4) if score_res.llm_semantic else 0.0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed single PR rank operation: {str(e)}")


async def _cache_results(ranked_results: List[PRScoreResult], repo_name: str):
    import json
    from pathlib import Path
    cache_file = Path(__file__).parent / f"cache_{repo_name.replace('/', '_')}.json"
    try:
        data = [{"pr_number": r.pr_number, "weighted_score": r.weighted_score, "tier": r.tier.value, "timestamp": datetime.now().isoformat()} for r in ranked_results]
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Start the server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("🚀 Starting PR Business Impact Ranking API (Resilient Mode)")
    print("=" * 80)
    print(f"\n📍 API URL: http://localhost:8002")
    print(f"📚 API Docs: http://localhost:8002/docs")
    print("\nPress Ctrl+C to stop\n")
    
    # "api:app" means: look inside api.py for the variable named 'app'
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )