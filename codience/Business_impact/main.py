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
from pydantic import BaseModel, Field

# Import your existing modules
from models import PRPayload, RankBatchRequest, RankedPRList, PRScoreResult
from coreRanking import PRRankingEngine
from pr_fetcher import PRFetcherWithDotNet
from dotnet_jira_client import get_dotnet_client, fetch_authenticated_github_email
from dotenv import load_dotenv

load_dotenv()
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
# ... (keep your existing imports here)

# 1. Define the automatic background lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 80)
    print("⏳ [Lifecycle] Bootstrapping Application Dependencies...")
    print("=" * 80)

    # Validate essential environments
    required_envs = ["GITHUB_TOKEN", "DOTNET_API_URL"]
    missing = [env for env in required_envs if not os.getenv(env)]
    if missing:
        critical_msg = f"CRITICAL BOOT ERROR: Missing environment variables: {missing}"
        print(f"❌ {critical_msg}")
        # Shuts down the application worker process safely before accepting traffic
        raise RuntimeError(critical_msg)

    # Validate or spin up Ollama inside the running event loop
    print("⏳ [Lifecycle] Verifying Ollama local inference service...")
    ollama_ready = False
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            res = await client.get("http://127.0.0.1:11434/api/tags")
            if res.status_code == 200:
                print("   ✓ Ollama service detected running locally.")
                ollama_ready = True
        except httpx.ConnectError:
            print("⚠️ Ollama offline. Attempting automatic micro-service execution...")
            try:
                import subprocess
                import sys
                if sys.platform == "win32":
                    subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Await readiness gracefully inside the event loop
                for _ in range(5):
                    await asyncio.sleep(2)
                    try:
                        check = await client.get("http://127.0.0.1:11434/api/tags")
                        if check.status_code == 200:
                            print("   ✓ Ollama service successfully initialized.")
                            ollama_ready = True
                            break
                    except Exception:
                        continue
            except Exception as e:
                print(f"❌ Could not run background subprocess call for Ollama: {e}")

    if not ollama_ready:
        print("⚠️ Warning: Running pipeline without a verified local model instance. Semantic scores will fail.")

    print("🚀 [Lifecycle] Application dependency verification complete. Standing up API routers...")
    yield #----------------- Server yields here and begins serving routes -----------------#
    print("🛑 [Lifecycle] Shaking down engine components...")


# 2. Inject the lifespan handler directly into your FastAPI application setup
app = FastAPI(
    title="PR Business Impact Ranking API",
    description="API for ranking pull requests by business impact using local AI models",
    version="1.0.0",
    lifespan=lifespan # 👈 Injected here
)

# ... (Leave all the rest of your app routes, middleware, and engine instantiations exactly as they are)
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
 #---------------------------------------------------------------------------
# Ranking Endpoints (Optimized & New)
# ---------------------------------------------------------------------------

@app.get("/api/rank/pr/{owner}/{repo}/{pr_number}")
async def rank_single_pr_by_id(owner: str, repo: str, pr_number: int):
    """
    Fetch and evaluate a single Pull Request by its explicit number immediately,
    bypassing heavy open-PR batch sweeps.
    """
    try:
        repo_name = f"{owner}/{repo}"
        user_email = fetch_authenticated_github_email() or "unknown@domain.internal"
        
        if not pr_fetcher.github:
            raise HTTPException(status_code=401, detail="GitHub Client uninitialized. Set GITHUB_TOKEN.")

        # 1. Directly fetch targeted single PR from GitHub (O(1) search)
        try:
            raw_pr_data = pr_fetcher.github.get_pull_request(owner, repo, pr_number)
        except Exception:
            raise HTTPException(status_code=404, detail=f"PR #{pr_number} could not be found or accessed in {repo_name}")

        # 2. Convert and enrich using direct structural calls
        payload = pr_fetcher._github_pr_to_dict(raw_pr_data, owner, repo)
        enriched_payload = pr_fetcher.pr_enricher.enrich_pr_with_jira(payload, fallback_email=user_email)
        target_pr = pr_fetcher._dict_to_pr_payload(enriched_payload, raw_pr_data, owner, repo)
            
        # 3. Execute calculation pipeline directly 
        score_res: PRScoreResult = await ranking_engine.score_single_pr(target_pr, reporter_email=user_email)
        
        # 4. Structure output tracking payload precisely
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

class JiraConfigPayload(BaseModel):
    jira_api_token: str = Field(..., description="The Jira Personal Access Token or API Token")
    jira_cloud_id: str = Field(..., description="Jira Cloud Tenant Site ID or Base URL instance")
    jira_project_key: str = Field(..., description="Target Jira Project Key Prefix (e.g., PROJ)")
# Initialize FastAPI

@app.post("/api/rank/pr/{owner}/{repo}/{pr_number}/with-config")
async def rank_single_pr_with_explicit_config(
    owner: str, 
    repo: str, 
    pr_number: int, 
    config: JiraConfigPayload
):
    """
    Fetch and evaluate a single PR by dynamically overriding target Jira configurations 
    provided straight from the incoming JSON payload instead of global .env attributes.
    """
    try:
        repo_name = f"{owner}/{repo}"
        user_email = fetch_authenticated_github_email() or "unknown@domain.internal"
        
        if not pr_fetcher.github:
            raise HTTPException(status_code=401, detail="GitHub Client uninitialized.")

        # 1. Direct targeted retrieval
        try:
            raw_pr_data = pr_fetcher.github.get_pull_request(owner, repo, pr_number)
        except Exception:
            raise HTTPException(status_code=404, detail=f"PR #{pr_number} could not be resolved from {repo_name}")

        # 2. Build dictionary payload
        payload = pr_fetcher._github_pr_to_dict(raw_pr_data, owner, repo)
        
        # 3. CRITICAL: Inject dynamic client tokens into execution context instead of system env
        # Pass the custom tokens directly down into the specialized .NET backend wrapper context
        enriched_payload = pr_fetcher.pr_enricher.enrich_pr_with_explicit_jira_config(
            payload, 
            fallback_email=user_email,
            token=config.jira_api_token,
            cloud_id=config.jira_cloud_id,
            project_key=config.jira_project_key
        )
        
        # 4. Generate structured models and calculate
        target_pr = pr_fetcher._dict_to_pr_payload(enriched_payload, raw_pr_data, owner, repo)
        score_res: PRScoreResult = await ranking_engine.score_single_pr(target_pr, reporter_email=user_email)
        
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
                "formula_score": round(bd.get("formula_score", bd.get("business_impact", 0.0) / 100.0), 6),
                "local_model_score": round(score_res.llm_semantic.raw_score, 4) if score_res.llm_semantic else 0.0,
                "business_impact": round(score_res.weighted_score, 4),

            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dynamic configuration ranking route failed: {str(e)}")
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
    print(f"\n📍 API URL: http://localhost:8003")
    print(f"📚 API Docs: http://localhost:8003/docs")
    print(f"🔍 Health: http://localhost:8003/health")
    print("\nPress Ctrl+C to stop\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )