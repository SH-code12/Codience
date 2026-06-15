import os
import sys

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from summarize_pr import summarize_pr



BACKEND_BASE_URL = "http://127.0.0.1:5051/api/GitHubAuth"



def _log(message: str):
    print(message, file=sys.stderr)


app = FastAPI(title="Codience PR Summarizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PRInput(BaseModel):
    title: str
    description: str = ""
    diff: str = ""


class SummaryResponse(BaseModel):
    summary: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/summarize", response_model=SummaryResponse)
def summarize(data: PRInput):
    """Summarize what happened in a pull request. Returns a markdown summary."""
    summary = summarize_pr(data.model_dump())
    return {"summary": summary}


@app.get("/summarize/{owner}/{repo}/pulls/{pull_number}", response_model=SummaryResponse)
async def summarize_from_backend(owner: str, repo: str, pull_number: int):
    """Fetch a single PR from the .NET backend and return its summary.

    Calls GET {BACKEND_BASE_URL}/{owner}/{repo}/pulls/{pull_number} (which
    returns just that PR, diff included) and feeds its title/body/diff into
    the summarizer.
    """
    url = f"{BACKEND_BASE_URL}/{owner}/{repo}/pulls/{pull_number}"

    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        try:
            response = await client.get(url)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach backend at {url}: {exc!r}",
            )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Backend returned {response.status_code}: {response.text}",
        )

    pr = response.json()

    diff = pr.get("diffContent") or ""
    # The backend stores fetch failures as the diff text itself ("ERROR: ...").
    if diff.startswith("ERROR:"):
        _log(f"Backend could not provide a diff for PR #{pull_number}: {diff[:200]}")
        diff = ""

    pr_data = {
        "title": pr.get("title") or "",
        "description": pr.get("body") or "",
        "diff": diff,
    }

    summary = summarize_pr(pr_data)
    return {"summary": summary}
