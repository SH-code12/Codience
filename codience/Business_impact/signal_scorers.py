"""
signal_scorers.py
─────────────────
UserExposure and DeadlinePressure signals.

NOTE ON CITATIONS:
The formulas below are heuristics *inspired by* general findings in the
PR-prioritization literature (e.g. that severity, affected-user count, and
deadline proximity correlate with review urgency). They are not verified
transcriptions of a specific published equation. Treat the "AR-Prioritizer"
and "Gousios" references as informal attribution of inspiration, not as
citations of an exact formula — Azeem et al. (2020) is the actual AR-Prioritizer
paper; Olmedo & Barbeito (2024) published a related but distinct PR-integration
tool ("IPOptimizer").

UI = α·log(1 + users) + β·severity + γ·revenue   (heuristic, 0-1 scaled)
"""

import math
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

# FIX: "critical" was 9.0 (10x every other entry on this 0-1 scale).
# That one typo alone could blow out severity_score and silently inflate
# every downstream score for any PR linked to a "critical"-severity ticket.
JIRA_SEV_MAP: dict[str, float] = {
    "blocker": 1.00, "critical": 0.90,
    "major": 0.65, "high": 0.70,
    "medium": 0.50, "normal": 0.50,
    "minor": 0.25, "low": 0.20,
    "trivial": 0.10,
}

BUCKET_SCORE = {
    UserExposureBucket.CRITICAL: 0.90,
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
    severity_score = max(
        (JIRA_SEV_MAP.get(t.severity.lower(), 0.3) for t in jira_tickets),
        default=0.3
    )
    if max_users > 10_000:
        users_bucket = UserExposureBucket.CRITICAL
    elif max_users > 500:
        users_bucket = UserExposureBucket.MAJOR
    else:
        users_bucket = UserExposureBucket.MINOR

    revenue_flag = 1.0 if any(
        k in (pr_title + pr_body).lower()
        for k in ["payment", "billing", "checkout", "invoice", "subscription"]
    ) else 0.25

    final_bucket = min(
        [kw_bucket, jira_bucket, label_bucket, users_bucket],
        key=lambda b: BUCKET_RANK.index(b),
    )

    # α·log(1+users) + β·severity + γ·revenue
    alpha, beta, gamma = 0.5, 0.3, 0.2
    ui_raw = (
        alpha * math.log(1 + max_users) +
        beta * severity_score +
        gamma * revenue_flag
    )

    # FIX: previously two competing normalizations were computed
    # (`normalized_score = ui_raw/5.0` AND `score = ui_raw/10.0`) and only
    # `normalized_score` was actually returned — the `score` line was dead
    # code, which made the divisor choice look unintentional/undocumented.
    # log(1+users) maxes out in the low single digits even for huge user
    # counts (e.g. log(1+1,000,000) ≈ 13.8), so /5.0 was already saturating
    # ui_raw to 1.0 for any large incident. We use a softer divisor (8.0)
    # so the bucket (which already captures "is this huge") does more of the
    # categorical work and the continuous score keeps some dynamic range.
    normalized_score = min(ui_raw / 8.0, 1.0)

    parts = []
    if kw_hits:
        parts.append(f"keywords: {kw_hits}")
    if worst_sev != "unknown":
        parts.append(f"Jira severity: {worst_sev}")
    if max_users:
        parts.append(f"{max_users:,} users affected")

    return UserExposureDetail(
        bucket=final_bucket,
        score=round(normalized_score, 4),
        matched_keywords=kw_hits,
        jira_severity=worst_sev,
        explanation=(
            f"UI = {alpha}*log(1+{max_users}) + {beta}*{severity_score:.2f} "
            f"+ {gamma}*{revenue_flag} = {ui_raw:.3f} -> normalized {normalized_score:.4f}"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# DEADLINE PRESSURE
# DP = 1 / (1 + e^(k * days))
# ─────────────────────────────────────────────────────────────────────────────

def score_deadline(jira_tickets, milestone):

    today = date.today()

    dates = []
    for t in jira_tickets:
        for d in [t.sprint_end_date, t.milestone_due_date]:
            if d:
                try:
                    dates.append(datetime.fromisoformat(d).date())
                except Exception:
                    pass

    if milestone:
        try:
            dates.append(datetime.fromisoformat(milestone).date())
        except Exception:
            pass

    if not dates:
        return DeadlineDetail(
            days_remaining=None,
            source="none",
            score=0.1,
            explanation="no deadline signal"
        )

    nearest = min(dates)
    days_signed = (nearest - today).days  # FIX: keep sign before clamping

    # FIX (important behavior bug): `days` was clamped to >= 0 *before* being
    # passed into the sigmoid, so an overdue deadline (days_signed < 0) was
    # scored identically to "due today" (days_signed == 0) — both became 0.
    # An overdue PR should register *more* pressure than one due today, not
    # the same. We now let the sigmoid see the real signed value and only
    # clamp `days_remaining` for display purposes.
    k = 0.15
    dp = 1 / (1 + math.exp(k * days_signed))

    days_display = max(days_signed, 0)
    source = "milestone" if milestone and not any(
        t.sprint_end_date or t.milestone_due_date for t in jira_tickets
    ) else ("sprint" if any(t.sprint_end_date for t in jira_tickets) else "milestone")

    return DeadlineDetail(
        days_remaining=days_display,
        source=source,
        score=round(dp, 4),
        explanation=f"{days_signed} days remaining (sigmoid pressure, k={k})"
    )