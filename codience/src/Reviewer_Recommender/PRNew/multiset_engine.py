"""
multiset_engine.py
──────────────────
Implements the reviewer-profile mathematics from:
  "Reviewer Recommendation Using Reviewers' Profiles" (J Intell Inf Syst, 2018)

Key ideas used here
-------------------
1. m(C)   — multiset representation of a commit's file paths
             Each path is tokenised into words; word frequencies are summed.

2. P(R)   — reviewer profile = multiset-union of m(C) over all commits
             reviewed by R.  Here we build P(R) ON DEMAND from a list of
             commits — no persistent profile store is required.

3. T(X,Y) — Tversky similarity adapted to multisets
             T(X,Y) = |X∩Y| / (|X∩Y| + α|X-Y| + β|Y-X|)
             α=0.5, β=0.5  →  equivalent to Jaccard (paper's default)
             α=0.1, β=0.9  →  weights profile (X) more than commit (Y)

4. ex(d)  — time-decay extinguishing factor
             ex(d) = (l/f)^d   where d = days since commit,
             f = decay strength (e.g. 2), l = half-life in days (e.g. 180)
             After `l` days the word frequency is multiplied by 1/f.

5. Jaccard — provided as a baseline / cross-check.
"""

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Optional


# ── Defaults (all tunable via constructor or function args) ────────────────────

DEFAULT_ALPHA          = 0.5    # Tversky α — weight of profile-only tokens
DEFAULT_BETA           = 0.5    # Tversky β — weight of commit-only tokens
DEFAULT_DECAY_FACTOR   = 2.0    # f: after l days, score halved
DEFAULT_DECAY_HALFLIFE = 180    # l: half-life in days
USE_DECAY_BY_DEFAULT   = True


# ── Path tokenisation ──────────────────────────────────────────────────────────

_SPLIT_RE = re.compile(r"[/\\._\-\s]+")


def tokenise_path(path: str) -> list[str]:
    """
    Splits a file path into lowercase words (path segments + filename stem).

    "src/main/java/package1/SomeClass.java"
    → ["src", "main", "java", "package1", "someclass", "java"]

    CamelCase is NOT split (matches the paper's approach of treating file-name
    and directory tokens as atomic units).
    """
    raw = _SPLIT_RE.split(path.lower())
    return [tok for tok in raw if tok]


def commit_multiset(file_paths: list[str]) -> Counter:
    """
    m(C) — multiset representation of a commit.

    Args:
        file_paths: list of file path strings modified in the commit.

    Returns:
        Counter mapping each path token to its total frequency across all paths.
    """
    result: Counter = Counter()
    for path in file_paths:
        result.update(tokenise_path(path))
    return result


# ── Time-decay extinguishing factor ───────────────────────────────────────────

def extinguish(days: float, decay_factor: float = DEFAULT_DECAY_FACTOR,
               halflife_days: float = DEFAULT_DECAY_HALFLIFE) -> float:
    """
    ex(d) = (l / f)^d  normalised so ex(0) = 1 and ex(halflife) = 1/f.

    The paper defines:  ex(d) = (l/f)^d
    With l=halflife_days and f=decay_factor this becomes:
        ex(d) = (halflife / decay_factor) ^ d
    which diverges for large d.  The practical implementation (matching the
    paper's intent) is:
        ex(d) = (1/f) ^ (d / l)   →   f^(-d/l)
    So after l days the multiplier is 1/f; after 2l days it is 1/f².
    """
    if days <= 0:
        return 1.0
    return math.pow(decay_factor, -(days / halflife_days))


# ── Reviewer profile construction ──────────────────────────────────────────────

def build_reviewer_profile(
    commits: list[dict],
    use_decay: bool = USE_DECAY_BY_DEFAULT,
    decay_factor: float = DEFAULT_DECAY_FACTOR,
    halflife_days: float = DEFAULT_DECAY_HALFLIFE,
    reference_date: Optional[datetime] = None,
) -> Counter:
    """
    P(R) — on-demand reviewer profile built from a list of commit dicts.

    Each commit dict must contain:
        "files"  : list of file path strings  (required)
        "date"   : ISO-8601 datetime string   (required when use_decay=True)

    When use_decay=True each token frequency is multiplied by ex(age_in_days)
    before being added to the profile — older commits contribute less.

    Returns:
        Counter  (can contain float values when decay is enabled)
    """
    ref = reference_date or datetime.now(timezone.utc)
    profile: Counter = Counter()

    for commit in commits:
        paths  = commit.get("files", [])
        m_c    = commit_multiset(paths)

        if use_decay and m_c:
            raw_date = commit.get("date", "")
            age_days = _age_in_days(raw_date, ref)
            factor   = extinguish(age_days, decay_factor, halflife_days)
            weighted = {tok: freq * factor for tok, freq in m_c.items()}
            profile.update(weighted)
        else:
            profile.update(m_c)

    return profile


def _age_in_days(date_str: str, ref: datetime) -> float:
    if not date_str:
        return 365.0
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (ref - dt).total_seconds() / 86400.0)
    except Exception:
        return 365.0


# ── Multiset set-operations ────────────────────────────────────────────────────

def _intersection_size(x: Counter, y: Counter) -> float:
    """Sum of min(x[k], y[k]) for all shared keys."""
    shared = set(x) & set(y)
    return sum(min(x[k], y[k]) for k in shared)


def _x_minus_y_size(x: Counter, y: Counter) -> float:
    """Sum of max(0, x[k] - y[k]) for all keys in x."""
    return sum(max(0.0, x[k] - y.get(k, 0)) for k in x)


# ── Similarity functions ───────────────────────────────────────────────────────

def tversky_similarity(
    profile: Counter,
    commit_m: Counter,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    """
    T(P, m(C)) = |P∩m(C)| / (|P∩m(C)| + α|P−m(C)| + β|m(C)−P|)

    α controls how much the profile-only tokens penalise the score.
    β controls how much the commit-only tokens penalise the score.

    α=β=0.5  →  Jaccard equivalent (paper's symmetric baseline).
    α=0.1, β=0.9  →  favour reviewers whose profile is a superset of the commit.
    """
    if not profile or not commit_m:
        return 0.0

    inter   = _intersection_size(profile, commit_m)
    p_only  = _x_minus_y_size(profile, commit_m)
    c_only  = _x_minus_y_size(commit_m, profile)

    denom = inter + alpha * p_only + beta * c_only
    return (inter / denom) if denom > 0 else 0.0


def jaccard_similarity(profile: Counter, commit_m: Counter) -> float:
    """
    J(P, m(C)) = |P∩m(C)| / |P∪m(C)|

    Baseline function used in the paper.  Equivalent to Tversky(α=0.5, β=0.5).
    """
    if not profile or not commit_m:
        return 0.0

    inter = _intersection_size(profile, commit_m)
    union = sum((profile + commit_m).values()) - inter   # |P| + |m(C)| - |P∩m(C)|
    return (inter / union) if union > 0 else 0.0


# ── Convenience: score one reviewer against a PR commit ───────────────────────

def score_reviewer(
    reviewer_commits: list[dict],
    pr_file_paths: list[str],
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    use_decay: bool = USE_DECAY_BY_DEFAULT,
    decay_factor: float = DEFAULT_DECAY_FACTOR,
    halflife_days: float = DEFAULT_DECAY_HALFLIFE,
    reference_date: Optional[datetime] = None,
) -> dict:
    """
    Computes both Tversky and Jaccard similarity for a single reviewer.

    Args:
        reviewer_commits : list of commit dicts  { files: [...], date: "..." }
        pr_file_paths    : file paths changed in the incoming PR

    Returns:
        {
          "tversky"  : float 0-1,
          "jaccard"  : float 0-1,
          "profile_size": int   (number of unique tokens in profile),
          "commit_size" : int,
        }
    """
    ref      = reference_date or datetime.now(timezone.utc)
    profile  = build_reviewer_profile(reviewer_commits, use_decay, decay_factor,
                                      halflife_days, ref)
    m_c      = commit_multiset(pr_file_paths)

    return {
        "tversky":      round(tversky_similarity(profile, m_c, alpha, beta), 6),
        "jaccard":      round(jaccard_similarity(profile, m_c), 6),
        "profile_size": len(profile),
        "commit_size":  len(m_c),
    }