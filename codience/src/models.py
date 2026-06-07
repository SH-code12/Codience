from typing import Optional, Any
from pydantic import BaseModel, Field

class BaseRepoRequest(BaseModel):
    owner: str = Field(..., description="GitHub repository owner or organization.")
    repo: str = Field(..., description="GitHub repository name.")
    pr_number: int = Field(..., description="Pull request number.")


class RankingOptions(BaseModel):
    top_k: Optional[int] = Field(default=None, description="Max recommendations (1-20). Default 5.")


class RecommendReviewersRequest(BaseRepoRequest):
    required_reviewers: list[Any] = Field(default_factory=list, description="Explicit reviewers to consider (strings or dicts).")
    options: Optional[RankingOptions] = None
    jira_token: Optional[str] = None
    jira_cloud_id: Optional[str] = None
    jira_project_key: Optional[str] = None


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
