import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from summarize_pr import summarize_pr



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
