"""
scorer_agent.py - Enhanced scorer with Tversky similarity + AI + formula
"""

import json
import math
import re
import os
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict
from collections import Counter

from pydantic import BaseModel, ValidationError
import sys
sys.path.insert(0, '/home/shahd/Desktop/Grduation/codience/src/Reviewer_Recommender/PRNew')

from .llm import generate_with_resilience
from .multiset_engine import (
    commit_multiset,
    build_reviewer_profile,
    tversky_similarity,
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    DEFAULT_DECAY_FACTOR,
    DEFAULT_DECAY_HALFLIFE,
)
from .profile_cache import ProfileCache
from .prompts import SCORER_PROMPT

# ── Weights (must sum to 1.0) ──────────────────────────────────────────────────
SCORE_WEIGHTS = {
    "tversky": 0.45,
    "ai": 0.30,
    "recency": 0.20,
    "tenure": 0.05,
}
assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-6

REQUIRED_BOOST = 1.12
TENURE_NORMALISE_DAYS = 1095.0

TVERSKY_ALPHA = float(os.getenv("TVERSKY_ALPHA", str(DEFAULT_ALPHA)))
TVERSKY_BETA = float(os.getenv("TVERSKY_BETA", str(DEFAULT_BETA)))
DECAY_FACTOR = float(os.getenv("DECAY_FACTOR", str(DEFAULT_DECAY_FACTOR)))
DECAY_HALFLIFE = float(os.getenv("DECAY_HALFLIFE", str(DEFAULT_DECAY_HALFLIFE)))

class CandidateScore(BaseModel):
    name: str
    confidence_score: int
    justification: str

def _tenure_score(tenure_days: float) -> float:
    """Log-normalized tenure score (0-1)."""
    if tenure_days <= 0:
        return 0.0
    return min(1.0, math.log1p(tenure_days) / math.log1p(TENURE_NORMALISE_DAYS))

def _tversky_bulk(
    candidates: List[dict],
    pr_file_paths: List[str],
    repo: str,
    cache: ProfileCache,
    ref: datetime,
) -> Dict[str, float]:
    """Bulk Tversky scoring with caching and debugging."""
    m_c = commit_multiset(pr_file_paths)
    pr_hash = ProfileCache.hash_pr(pr_file_paths)
    dtag = ProfileCache.decay_tag(DECAY_FACTOR, DECAY_HALFLIFE)
    out = {}
    
    # DEBUG: Print PR files
    print(f"\n🔍 DEBUG: PR has {len(pr_file_paths)} files")
    if pr_file_paths:
        print(f"   Sample PR files (first 5):")
        for f in pr_file_paths[:5]:
            print(f"     - {f}")
    
    for c in candidates:
        name = c.get("name", "")
        if not name:
            continue

        cached_sim = cache.get_similarity(repo, name, pr_hash)
        if cached_sim is not None:
            out[name] = cached_sim
            print(f"   📦 {name}: Tversky from cache = {cached_sim:.3f}")
            continue

        commit_history = c.get("commit_history", [])
        if not commit_history:
            print(f"   ⚠️ {name}: No commit history! Tversky = 0.0")
            out[name] = 0.0
            continue

        print(f"\n   🔄 {name}: Building profile from {len(commit_history)} commits")
        
        profile = cache.get_profile(repo, name, dtag)
        if profile is None:
            profile = build_reviewer_profile(
                commit_history,
                use_decay=True,
                decay_factor=DECAY_FACTOR,
                halflife_days=DECAY_HALFLIFE,
                reference_date=ref,
            )
            cache.set_profile(repo, name, profile, dtag)
            print(f"   ✅ {name}: Profile built with {len(profile)} unique file paths")
        else:
            print(f"   📦 {name}: Profile from cache with {len(profile)} unique paths")
        
        # DEBUG: Show top files from developer
        if profile:
            print(f"   📁 {name}'s top files (by weight):")
            top_files = sorted(profile.items(), key=lambda x: x[1], reverse=True)[:5]
            for file_path, weight in top_files:
                print(f"      - {file_path} (weight: {weight:.3f})")
        
        # DEBUG: Calculate overlap
        pr_set = set(pr_file_paths)
        dev_set = set(profile.keys())
        overlap = pr_set & dev_set
        print(f"   🔍 Overlap with PR: {len(overlap)} files")
        if overlap:
            print(f"      Common files: {', '.join(list(overlap)[:5])}")
        else:
            print(f"      ❌ NO file overlap found!")
            # Show what developer works on vs PR
            dev_sample = list(dev_set)[:3] if dev_set else []
            pr_sample = pr_file_paths[:3] if pr_file_paths else []
            print(f"      Developer sample: {dev_sample}")
            print(f"      PR sample: {pr_sample}")

        sim = tversky_similarity(profile, m_c, TVERSKY_ALPHA, TVERSKY_BETA)
        cache.set_similarity(repo, name, pr_hash, sim)
        out[name] = sim
        print(f"   📊 {name}: Tversky similarity = {sim:.4f}")

    return out

def _call_llm_scorer(
    pr_analysis: dict,
    rag_roles: list,
    candidates: List[dict],
    tv_by_name: Dict[str, float],
) -> List[dict]:
    """Call LLM for AI scoring with Tversky as context."""
    if not candidates:
        return []

    lines = []
    for i, c in enumerate(candidates, 1):
        name = c.get("name", f"Candidate_{i}")
        tv = tv_by_name.get(name, 0.0)
        
        rag_matches = c.get("rag_code_matches", [])
        rag_text = f"\n  Historically Matched Code Diffs: {' | '.join(rag_matches)[:500]}..." if rag_matches else ""
        
        jira_ctx = c.get("jira_context", {})
        jira_text = ""
        if jira_ctx:
            j_domain = jira_ctx.get("domain", "Unknown")
            j_skills = ", ".join(jira_ctx.get("recent_skills", []))
            j_summary = jira_ctx.get("summary", "")
            jira_text = f"\n  Jira Context: Domain={j_domain}, Skills={j_skills}, Summary={j_summary}"
        
        lines.append(
            f"Candidate {i}: {name}\n"
            f"  Tversky file-path similarity: {tv:.3f}\n"
            f"  Commit skills: {', '.join(c.get('commit_skills', [])) or 'none'}\n"
            f"  Explicit skills: {', '.join(c.get('raw_skills', [])) or 'none'}{rag_text}{jira_text}"
        )

    rag_ctx = "\n".join(f"- {r.page_content}" for r in rag_roles) if rag_roles else "No vector DB match."
    
    pr_skills_str = ", ".join(pr_analysis.get("required_skills", []))
    pr_langs_str = ", ".join(pr_analysis.get("detected_languages", []))
    seniority = ", ".join(pr_analysis.get("seniority_signals", [])) or "none"

    prompt = SCORER_PROMPT.format(
        pr_skills=f"{pr_skills_str}; languages: {pr_langs_str}",
        pr_analysis_summary=pr_analysis.get("rag_query", pr_analysis.get("summary", "")),
        seniority_signals=seniority,
        rag_context=rag_ctx,
        candidates_text="\n\n".join(lines),
    )

    result = generate_with_resilience(prompt, purpose="candidate_scoring")
    if not result.get("ok"):
        print(f"⚠️ Scorer LLM failed: {result.get('reason')}")
        return []

    try:
        cleaned = re.sub(r"```(?:json)?|```", "", result.get("text", "")).strip()
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        parsed = json.loads(match.group() if match else cleaned)
        return [CandidateScore(**item).model_dump() for item in parsed]
    except Exception as exc:
        print(f"⚠️ Scorer parse error: {exc}")
        return []

def calculate_match_scores(
    pr_analysis: Dict[str, Any],
    rag_roles: List,
    candidates: List[Dict[str, Any]],
    pr_file_paths: List[str] = None,
    repo: str = "unknown",
    cache: Optional[ProfileCache] = None,
    prioritize_recent: bool = True,
    ref_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Score all candidates using Tversky + AI + supporting signals.
    
    Each candidate dict can have:
        - name (required)
        - commit_history: [{"files": [str], "date": "ISO-str"}]
        - commit_skills: [str]
        - raw_skills: [str]
        - tenure_days: float
        - recency_score: float
        - required_reviewer: bool
    """
    if not candidates:
        return []
    
    if pr_file_paths is None:
        pr_file_paths = []
    
    cache = cache or ProfileCache()
    ref = ref_date or datetime.now(timezone.utc)
    
    pr_skills = set(pr_analysis.get("required_skills", []))
    pr_languages = set(pr_analysis.get("detected_languages", []))
    
    # 1. Tversky scores (cached)
    tv_scores = _tversky_bulk(candidates, pr_file_paths, repo, cache, ref)
    print(f"  📊 Tversky: scored {len(tv_scores)} candidates.")
    
    # 2. AI scores
    ai_results = _call_llm_scorer(pr_analysis, rag_roles, candidates, tv_scores)
    ai_by_name = {r["name"].lower(): r for r in ai_results}
    
    # 3. Apply formula
    final = []
    for c in candidates:
        name = c.get("name", "")
        if not name:
            continue
        
        name_key = name.lower()
        ai_entry = ai_by_name.get(name_key, {})
        ai_s = float(ai_entry.get("confidence_score", 0)) / 100.0
        tv_s = tv_scores.get(name, 0.0)
        tenure_s = _tenure_score(c.get("tenure_days", 365))
        rec_s = float(c.get("recency_score", 0.0))
        required = bool(c.get("required_reviewer", False))
        
        w = dict(SCORE_WEIGHTS)
        if not prioritize_recent:
            w["tversky"] += w["recency"]
            w["recency"] = 0.0
        
        composite = (
            w["tversky"] * tv_s +
            w["ai"] * ai_s +
            w["recency"] * rec_s +
            w["tenure"] * tenure_s
        )
        if required:
            composite = min(1.0, composite * REQUIRED_BOOST)
        
        final_int = max(0, min(100, round(composite * 100)))
        
        reasons = []
        if required:
            reasons.append("required_reviewer")
        if tv_s >= 0.3:
            reasons.append("strong_file_overlap")
        if rec_s >= 0.5:
            reasons.append("recent_activity")
        if tenure_s >= 0.7:
            reasons.append("long_tenure")
        
        final.append({
            "name": name,
            "confidence_score": final_int,
            "justification": ai_entry.get("justification", f"Tversky={tv_s:.2f}, AI={ai_s:.2f}"),
            "reasons": reasons,
            "required_reviewer": required,
            "score_breakdown": {
                "tversky_score": round(tv_s, 4),
                "ai_score": round(ai_s, 4),
                "recency_score": round(rec_s, 4),
                "tenure_score": round(tenure_s, 4),
                "composite": round(composite, 4),
                "weights": {k: round(v, 2) for k, v in SCORE_WEIGHTS.items()},
            },
        })
    
    if not ai_results:
        print("⚠️ Tversky-only fallback ranking (LLM unavailable).")
        for entry in final:
            entry["justification"] = f"Tversky={tv_scores.get(entry['name'], 0):.3f} (LLM fallback)"
    
    return sorted(final, key=lambda x: x["confidence_score"], reverse=True)