"""
models.py — Shared data contracts for the PR Business Impact Ranker.

Every field maps to research-backed features:
  - blast_radius   → Springer 2024, CodePlan 2023
  - user_exposure  → Olmedo & Barbeito 2024 (AR-Prioritizer)
  - deadline       → Yang 2023, Gousios integrator survey
  - llm_semantic   → CodePlan 2023
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


# ─── Enums ────────────────────────────────────────────────────────────────────

class ImpactTier(str, Enum):
    HIGH   = "high"    # score ≥ 70
    MEDIUM = "medium"  # score 40–69
    LOW    = "low"     # score  < 40

class UserExposureBucket(str, Enum):
    CRITICAL = "critical"   # payments, auth, data-loss paths
    MAJOR    = "major"      # user-facing product flows
    MINOR    = "minor"      # internal tooling / infra

class ComponentType(str, Enum):
    AUTHENTICATION = "authentication"
    PAYMENT = "payment"
    CHECKOUT = "checkout"
    DATABASE = "database"
    API_GATEWAY = "api_gateway"
    USER_INTERFACE = "user_interface"
    INFRASTRUCTURE = "infrastructure"
    INTERNAL_TOOL = "internal_tool"

class SecurityRiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


# ─── Inputs ───────────────────────────────────────────────────────────────────

class JiraTicket(BaseModel):
    key: str
    summary: str
    severity: str                        # Blocker / Critical / Major / Minor / Low
    priority: str
    labels: list[str] = []
    affected_users_count: Optional[int] = None
    sprint_end_date: Optional[str] = None      # ISO-8601
    milestone_due_date: Optional[str] = None   # ISO-8601
    description: str = ""
    status: str = ""


class PRPayload(BaseModel):
    """Single PR to be scored. Sent by the .NET backend."""
    pr_number:   int
    pr_title:    str
    pr_body:     str = ""
    repo_owner:  str
    repo_name:   str
    head_branch: str = ""
    base_branch: str = "main"

    # Code signals (filled by .NET after fetching from GitHub)
    diff_excerpt:  str = ""          # first ~6 000 chars of unified diff
    changed_files: list[str] = []

    # Metadata
    github_labels:        list[str] = []
    milestone_due_date:   Optional[str] = None
    linked_jira_tickets:  list[JiraTicket] = []


class RankBatchRequest(BaseModel):
    """Rank a list of PRs and return them sorted by business impact."""
    prs: list[PRPayload]


# ─── Sub-scores (one per signal) ─────────────────────────────────────────────

class BlastRadiusDetail(BaseModel):
    """
    Measures how many internal/external components depend on the changed code.
    Based on: call-graph depth (Springer 2024) + API surface change (CodePlan 2023).
    """
    internal_callers:      int   = 0
    external_api_routes:   int   = 0
    critical_files_hit:    int   = 0
    score:                 float = Field(ge=0, le=1)
    explanation:           str   = ""


class UserExposureDetail(BaseModel):
    """
    How many users / how much revenue is exposed to this change.
    Based on: AR-Prioritizer (Olmedo 2024) — Jira severity + user count.
    """
    bucket:           UserExposureBucket
    score:            float = Field(ge=0, le=1)
    matched_keywords: list[str] = []
    jira_severity:    str = ""
    explanation:      str = ""


class DeadlineDetail(BaseModel):
    """
    Time pressure from sprint / milestone deadlines.
    Based on: Gousios integrator survey — deadline proximity is top-3 factor.
    """
    days_remaining:  Optional[int] = None
    source:          str = "none"          # sprint | milestone | none
    score:           float = Field(ge=0, le=1)
    explanation:     str = ""


class LLMSemanticDetail(BaseModel):
    """
    Semantic understanding of diff + Jira context via LLM.
    Based on: CodePlan 2023 — LLM reasoning over dependency changes.
    """
    business_summary:    str
    affected_systems:    list[str] = []
    user_impact_bucket:  UserExposureBucket
    raw_score:           float = Field(ge=0, le=1)
    confidence:          float = Field(ge=0, le=1)
    final_score:         float = Field(ge=0, le=1)   # raw × confidence
    model_used:          str = ""


# ─── Final result per PR ──────────────────────────────────────────────────────

class PRScoreResult(BaseModel):
    pr_number:   int
    pr_title:    str
    repo:        str

    # Sub-scores
    blast_radius:   BlastRadiusDetail
    user_exposure:  UserExposureDetail
    deadline:       DeadlineDetail
    llm_semantic:   LLMSemanticDetail

    # Aggregated
    weighted_score:              float          # 0–100
    tier:                        ImpactTier
    score_breakdown:             dict           # per-signal contributions
    recommended_reviewers:       int
    should_block_merge:          bool
    github_comment_markdown:     str
    processing_ms:               int


# ─── Ranked list result ───────────────────────────────────────────────────────

class RankedPRList(BaseModel):
    total: int
    ranked: list[PRScoreResult]             # sorted descending by weighted_score
    high_count:   int
    medium_count: int
    low_count:    int