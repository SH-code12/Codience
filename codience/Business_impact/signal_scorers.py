"""
signal_scorers.py
─────────────────
UserExposure and DeadlinePressure signals
"""

import re
from datetime import date, datetime
from models import UserExposureDetail, UserExposureBucket, DeadlineDetail, JiraTicket

# ─────────────────────────────────────────────────────────────────────────────
# USER EXPOSURE
# ─────────────────────────────────────────────────────────────────────────────

CRITICAL_KW = [
    "payment", "billing", "checkout", "invoice", "stripe", "paypal", "braintree",
    "transaction", "revenue", "charge", "refund", "subscription", "purchase",
    "auth", "authentication", "oauth", "jwt", "session", "password", "token",
    "2fa", "mfa", "sso", "saml", "login", "logout", "credential", "access control",
    "data loss", "corruption", "data integrity", "pii", "personal data",
    "gdpr", "compliance", "security", "vulnerability", "breach", "exploit",
]

MAJOR_KW = [
    "user", "customer", "account", "profile", "dashboard", "onboard", "signup", "register",
    "search", "feed", "notification", "email", "sms", "push",
    "checkout", "cart", "order", "product", "catalog", "listing",
    "api", "endpoint", "public", "external", "client", "consumer",
    "performance", "latency", "timeout", "slow", "degraded",
]

MINOR_KW = [
    "admin", "internal", "script", "cron", "batch", "job", "scheduled",
    "migration", "cleanup", "housekeeping", "refactor", "style", "lint", "format",
    "documentation", "readme", "test", "spec", "fixture", "mock",
    "infra", "devops", "ci", "cd", "pipeline", "logging", "metric", "monitoring",
    "dependency", "upgrade", "bump", "chore",
]

JIRA_SEV_MAP: dict[str, float] = {
    "blocker": 1.0, "critical": 1.0,
    "major": 0.65, "high": 0.80,
    "medium": 0.50, "normal": 0.50,
    "minor": 0.25, "low": 0.20,
    "trivial": 0.10,
}

BUCKET_SCORE = {
    UserExposureBucket.CRITICAL: 1.00,
    UserExposureBucket.MAJOR: 0.60,
    UserExposureBucket.MINOR: 0.20,
}

BUCKET_RANK = [
    UserExposureBucket.CRITICAL,
    UserExposureBucket.MAJOR,
    UserExposureBucket.MINOR,
]

def _kw_bucket(text: str) -> tuple[UserExposureBucket, list[str]]:
    lower = text.lower()
    c = [k for k in CRITICAL_KW if k in lower]
    if c:
        return UserExposureBucket.CRITICAL, c[:5]
    m = [k for k in MAJOR_KW if k in lower]
    if len(m) >= 2:
        return UserExposureBucket.MAJOR, m[:5]
    return UserExposureBucket.MINOR, [k for k in MINOR_KW if k in lower][:3]

def score_user_exposure(
    pr_title: str,
    pr_body: str,
    diff: str,
    jira_tickets: list[JiraTicket],
) -> UserExposureDetail:

    combined = f"{pr_title} {pr_body} {diff[:2000]}"
    kw_bucket, kw_hits = _kw_bucket(combined)

    jira_bucket = UserExposureBucket.MINOR
    worst_sev = "unknown"
    for t in jira_tickets:
        sev = t.severity.lower().strip()
        if sev in ("blocker", "critical"):
            jira_bucket = UserExposureBucket.CRITICAL
            worst_sev = t.severity
            break
        if sev in ("major", "high"):
            jira_bucket = UserExposureBucket.MAJOR
            worst_sev = t.severity

    label_text = " ".join(" ".join(t.labels) for t in jira_tickets)
    label_bucket, _ = _kw_bucket(label_text) if label_text else (UserExposureBucket.MINOR, [])

    max_users = max((t.affected_users_count or 0 for t in jira_tickets), default=0)
    if max_users > 10_000:
        users_bucket = UserExposureBucket.CRITICAL
    elif max_users > 500:
        users_bucket = UserExposureBucket.MAJOR
    else:
        users_bucket = UserExposureBucket.MINOR

    final_bucket = min(
        [kw_bucket, jira_bucket, label_bucket, users_bucket],
        key=lambda b: BUCKET_RANK.index(b),
    )

    parts = []
    if kw_hits:
        parts.append(f"keywords: {kw_hits}")
    if worst_sev != "unknown":
        parts.append(f"Jira severity: {worst_sev}")
    if max_users:
        parts.append(f"{max_users:,} users affected")

    return UserExposureDetail(
        bucket=final_bucket,
        score=round(BUCKET_SCORE[final_bucket], 4),
        matched_keywords=kw_hits,
        jira_severity=worst_sev,
        explanation="; ".join(parts) or "No strong user-exposure signal",
    )

# ─────────────────────────────────────────────────────────────────────────────
# DEADLINE PRESSURE
# ─────────────────────────────────────────────────────────────────────────────

def _parse_iso(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def _sigmoid_deadline(days: int) -> float:
    if days <= 0:
        return 1.0
    import math
    return round(max(1.0 / (1.0 + 0.15 * days), 0.10), 4)

def score_deadline(
    jira_tickets: list[JiraTicket],
    pr_milestone_due_date: str | None,
) -> DeadlineDetail:

    today = date.today()
    candidates: list[tuple[date, str]] = []

    for t in jira_tickets:
        for attr, label in [("sprint_end_date", "sprint"), ("milestone_due_date", "milestone")]:
            d = _parse_iso(getattr(t, attr))
            if d:
                candidates.append((d, label))

    d = _parse_iso(pr_milestone_due_date)
    if d:
        candidates.append((d, "milestone"))

    if not candidates:
        return DeadlineDetail(
            days_remaining=None, source="none", score=0.10,
            explanation="No sprint or milestone deadline found",
        )

    best_date, source = min(candidates, key=lambda x: x[0])
    days = max((best_date - today).days, 0)
    score = _sigmoid_deadline(days)

    if days == 0:
        expl = f"Deadline TODAY (source: {source}) 🚨"
    elif days <= 3:
        expl = f"{days}d to {source} deadline — critical urgency"
    elif days <= 7:
        expl = f"{days}d to {source} deadline — high pressure"
    elif days <= 14:
        expl = f"{days}d to {source} deadline — moderate pressure"
    else:
        expl = f"{days}d to {source} deadline"

    return DeadlineDetail(
        days_remaining=days, source=source, score=score, explanation=expl,
    )