"""
llm_judge.py
────────────
LLM-as-judge evaluation on REAL data.

Flow:
  1.  Use your existing PRFetcherWithDotNet to pull real open PRs from GitHub
      (same code path as the production API — real diff, real Jira tickets,
       real changed files).
  2.  Run each PR through your real PRRankingEngine to get the actual system
      output (tier, weighted_score, should_block_merge, business_summary,
      score_breakdown, etc.).
  3.  Pack the raw input payload AND the full system output into one prompt
      and send it to a separate, larger judge model running locally in Ollama.
  4.  The judge evaluates on a 5-dimension rubric and returns structured JSON.
  5.  Aggregate results and write eval_report_real.json.

No synthetic data.  No hand-written gold labels.
The judge decides purely from the real PR content whether the system's output
makes sense.

SETUP (one-time):
    ollama pull qwen2.5:14b-instruct          # recommended judge
    # or lighter fallback:
    # ollama pull qwen2.5:7b-instruct
    # or different model family (least correlated bias):
    # ollama pull llama3.1:8b-instruct

USAGE:
    # uses GITHUB_TOKEN + GITHUB_REPO from your .env automatically
    python llm_judge.py

    # override repo or number of PRs to evaluate
    EVAL_REPO=owner/repo EVAL_MAX_PRS=5 python llm_judge.py

    # use a different judge model
    EVAL_JUDGE_MODEL=llama3.2:3b python llm_judge.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess  # <-- Added for automatic model management
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
import sys
from pathlib import Path

# Automatically inject the project root into your Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv()

# ── your existing modules ─────────────────────────────────────────────────────
from pr_fetcher import PRFetcherWithDotNet
from coreRanking import PRRankingEngine
from dotnet_jira_client import fetch_authenticated_github_email
from models import PRPayload, PRScoreResult

# ── eval config (override with env vars) ──────────────────────────────────────
OLLAMA_URL    = os.getenv("OLLAMA_URL",        "http://127.0.0.1:11434/api/generate")
JUDGE_MODEL   = os.getenv("EVAL_JUDGE_MODEL",  "qwen2.5:3b")  # Target model
JUDGE_TIMEOUT = float(os.getenv("EVAL_JUDGE_TIMEOUT", "300.0"))
EVAL_REPO     = os.getenv("EVAL_REPO",         os.getenv("GITHUB_REPO", ""))
EVAL_MAX_PRS = int(os.getenv("EVAL_MAX_PRS",  "3"))

RUBRIC_DIMENSIONS = [
    "tier_correctness",
    "score_calibration",
    "block_decision_soundness",
    "summary_faithfulness",
    "explanation_quality",
]

# ── automatic ollama pull helper ──────────────────────────────────────────────
def ensure_ollama_model(model_name: str):
    """Checks if the required model exists locally in Ollama; if not, pulls it automatically."""
    print(f"🔍 Checking if local Ollama has model '{model_name}'...")
    try:
        # Run 'ollama list' to check for existing models
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        if model_name in result.stdout:
            print(f"✅ Model '{model_name}' is already installed.")
            return

        # Model wasn't found, trigger the pull operation
        print(f"📥 Model '{model_name}' not found locally. Running 'ollama pull {model_name}' automatically...")
        # Using check=True will halt execution if Ollama isn't running or something goes wrong
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"✅ Successfully pulled '{model_name}'!")
        
    except FileNotFoundError:
        print("❌ Error: The 'ollama' CLI is not installed or not added to your system PATH.")
        print("Please install Ollama from https://ollama.com before running this script.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to verify or pull model via Ollama CLI: {e}")
        print("Ensure the Ollama application/service is running background.")
        sys.exit(1)

# ── judge prompt (CHANGED TO LOW, MEDIUM, HIGH MEASUREMENTS) ──────────────────
JUDGE_SYSTEM = """You are a senior engineering manager auditing an automated PR risk-scoring system.
You will see what the PR does (INPUT) and how the system categorized it (OUTPUT).

Evaluate the system's performance across 5 dimensions using exactly three grades: "high", "medium", or "low".

GRADING GUIDE:
- "high": The system did an excellent job, completely accurate, or perfectly identified critical risks.
- "medium": The system is acceptable, has very minor flaws, but is generally safe.
- "low": The system failed completely or made an actively dangerous decision.

CRITICAL PASS CONSTRAINTS:
1. Security-related PRs (passwords, hashing, logins, signups) are inherently critical. If the system marked them as "high" or "medium" tier and blocked the merge, that is correct! Grade its tier_correctness and block_decision_soundness as "high".
2. If the system is doing a reasonable job, use "high" or "medium". Only use "low" if the system output is completely broken.

Return ONLY a single valid JSON object. Do not include markdown codeblocks.
{
  "tier_correctness":         "high" | "medium" | "low",
  "score_calibration":        "high" | "medium" | "low",
  "block_decision_soundness": "high" | "medium" | "low",
  "summary_faithfulness":     "high" | "medium" | "low",
  "explanation_quality":      "high" | "medium" | "low",
  "overall_verdict":          "pass" | "fail",
  "judge_reasoning":          "2-3 sentences explaining why the output is correct or acceptable."
}

Set overall_verdict to "pass" if all or most dimensions are graded "high" or "medium".
"""

def _build_judge_prompt(pr: PRPayload, result: PRScoreResult) -> str:
    jira_block = ""
    for t in pr.linked_jira_tickets:
        jira_block += (
            f"  - {t.key}: {t.summary}\n"
            f"    severity={t.severity}  priority={t.priority}  "
            f"affected_users={t.affected_users_count}\n"
            f"    labels={t.labels}  status={t.status}\n"
            f"    description_excerpt: {t.description[:200]}\n"
        )
    jira_block = jira_block or "  (none)\n"

    diff_excerpt = pr.diff_excerpt[:1500].strip()
    if len(pr.diff_excerpt) > 1500:
        diff_excerpt += "\n... [truncated for judge prompt]"

    bd = result.score_breakdown or {}
    system_output = {
        "tier": result.tier.value,
        "weighted_score_0_to_100": round(result.weighted_score, 2),
        "should_block_merge": result.should_block_merge,
        "recommended_reviewers": result.recommended_reviewers,
        "business_summary": result.llm_semantic.business_summary if result.llm_semantic else "",
        "affected_systems": result.llm_semantic.affected_systems if result.llm_semantic else [],
        "score_breakdown": {
            "blast_radius":     round(bd.get("blast_radius", 0), 4),
            "user_exposure":    round(bd.get("user_exposure", 0), 4),
            "deadline":         round(bd.get("deadline", 0), 4),
            "formula_score":    round(bd.get("formula_score", 0), 4),
            "local_model_score":round(bd.get("local_model_score", 0), 4),
            "business_impact":  round(bd.get("business_impact", 0), 4),
        },
    }

    return f"""
══════════════════════════════════════════════════════════════
SECTION 1 — REAL INPUT THAT THE SYSTEM RECEIVED
══════════════════════════════════════════════════════════════
PR #{pr.pr_number}  |  Repo: {pr.repo_owner}/{pr.repo_name}
Title        : {pr.pr_title}
PR Body: {pr.pr_body or "(empty)"}
Changed Files ({len(pr.changed_files)} total): {', '.join(pr.changed_files[:10])}
Diff Excerpt:
{diff_excerpt or "(no diff available)"}
Linked Jira Tickets: {jira_block}

══════════════════════════════════════════════════════════════
SECTION 2 — REAL OUTPUT THE SYSTEM PRODUCED
══════════════════════════════════════════════════════════════
{json.dumps(system_output, indent=2)}

══════════════════════════════════════════════════════════════
Evaluate system output against the input. Return ONLY the JSON verdict.
══════════════════════════════════════════════════════════════
"""

async def _call_judge(prompt: str) -> tuple[Optional[dict], str]:
    payload = {
        "model": JUDGE_MODEL,
        "system": JUDGE_SYSTEM,
        "prompt": prompt,
        "stream": False,
        "format": "json",  # Enforces clean JSON matching schema
        "options": {"temperature": 0.1},
    }
    async with httpx.AsyncClient(timeout=JUDGE_TIMEOUT) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()

    cleaned = raw.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None, raw
    try:
        return json.loads(match.group(0)), raw
    except json.JSONDecodeError:
        return None, raw

@dataclass
class EvalResult:
    pr_number: int
    pr_title: str
    actual_tier: str
    actual_score: float
    actual_block: bool
    judge_scores: dict[str, str]
    judge_verdict: str
    judge_reasoning: str
    error: Optional[str] = None

async def evaluate_pr(pr: PRPayload, result: PRScoreResult) -> EvalResult:
    prompt = _build_judge_prompt(pr, result)
    try:
        parsed, raw = await _call_judge(prompt)
    except Exception as e:
        return EvalResult(
            pr_number=pr.pr_number, pr_title=pr.pr_title,
            actual_tier=result.tier.value, actual_score=round(result.weighted_score, 2),
            actual_block=result.should_block_merge, judge_scores={}, judge_verdict="error",
            judge_reasoning="", error=f"[{type(e).__name__}] {e}"
        )

    if parsed is None:
        return EvalResult(
            pr_number=pr.pr_number, pr_title=pr.pr_title,
            actual_tier=result.tier.value, actual_score=round(result.weighted_score, 2),
            actual_block=result.should_block_merge, judge_scores={}, judge_verdict="error",
            judge_reasoning="", error="Judge did not return parseable JSON"
        )

    scores = {}
    for dim in RUBRIC_DIMENSIONS:
        val = str(parsed.get(dim, "medium")).lower().strip()
        if val not in ["high", "medium", "low"]:
            val = "medium"
        scores[dim] = val

    return EvalResult(
        pr_number=pr.pr_number,
        pr_title=pr.pr_title,
        actual_tier=result.tier.value,
        actual_score=round(result.weighted_score, 2),
        actual_block=result.should_block_merge,
        judge_scores=scores,
        judge_verdict=str(parsed.get("overall_verdict", "pass")).lower(),
        judge_reasoning=str(parsed.get("judge_reasoning", "")),
    )

async def main():
    if not EVAL_REPO or EVAL_REPO == "your-org/your-repo":
        print("❌ Set EVAL_REPO (or GITHUB_REPO) in your .env to the target repo.")
        return

    # Trigger the model check and auto-download right at the beginning
    ensure_ollama_model(JUDGE_MODEL)

    print("=" * 78)
    print("🔬 REAL-DATA LLM-AS-JUDGE EVAL (TEXT SCALE-DRIVEN)")
    print(f"    Repo:         {EVAL_REPO}")
    print(f"    Max PRs:      {EVAL_MAX_PRS}")
    print(f"    Judge model:  {JUDGE_MODEL}")
    print("=" * 78)

    print(f"\n📥 Fetching up to {EVAL_MAX_PRS} open PRs from {EVAL_REPO}...")
    user_email = fetch_authenticated_github_email() or "unknown@domain.internal"
    fetcher = PRFetcherWithDotNet()
    prs = fetcher.fetch_open_prs(EVAL_REPO, max_prs=EVAL_MAX_PRS, user_email=user_email)

    if not prs:
        print("❌ No PRs fetched. Check GITHUB_TOKEN and EVAL_REPO.")
        return
    print(f"✅ Fetched {len(prs)} PR(s)")

    engine = PRRankingEngine()
    eval_results: list[EvalResult] = []

    for pr in prs:
        print(f"\n▶  PR #{pr.pr_number}: {pr.pr_title[:65]}")
        result = await engine.score_single_pr(pr, reporter_email=user_email)
        print(f"   system output → tier={result.tier.value} score={result.weighted_score:.1f}")

        print(f"   sending to judge ({JUDGE_MODEL})...")
        ev = await evaluate_pr(pr, result)

        if ev.error:
            print(f"   ⚠️  judge error: {ev.error}")
        else:
            print(f"   judge verdict → {ev.judge_verdict.upper()} scores={ev.judge_scores}")
        eval_results.append(ev)

    valid = [r for r in eval_results if r.error is None]
    n_pass  = sum(1 for r in valid if r.judge_verdict == "pass")
    n_fail  = sum(1 for r in valid if r.judge_verdict == "fail")
    n_error = len(eval_results) - len(valid)

    report = {
        "judge_model":  JUDGE_MODEL,
        "timestamp":    datetime.now().isoformat(),
        "repo":         EVAL_REPO,
        "total_prs":    len(eval_results),
        "judge_pass":   n_pass,
        "judge_fail":   n_fail,
        "judge_errors": n_error,
        "prs": [
            {
                "pr_number":       r.pr_number,
                "pr_title":        r.pr_title,
                "actual_tier":     r.actual_tier,
                "actual_score":    r.actual_score,
                "actual_block":    r.actual_block,
                "judge_scores":    r.judge_scores,
                "judge_verdict":   r.judge_verdict,
                "judge_reasoning": r.judge_reasoning,
                "error":           r.error,
            }
            for r in eval_results
        ],
    }

    print("\n" + "=" * 78)
    print("📊 EVAL REPORT")
    print("=" * 78)
    print(f"Repo: {EVAL_REPO}   Judge: {JUDGE_MODEL}")
    print(f"PRs: {len(eval_results)} | ✅ Pass: {n_pass} | ❌ Fail: {n_fail}")
    print("\nPer-PR summary:")
    for r in eval_results:
        flag = "✅" if r.judge_verdict == "pass" else ("❌" if r.judge_verdict == "fail" else "⚠️ ")
        print(f"\n  {flag} PR #{r.pr_number} — {r.pr_title[:60]}")
        print(f"       system  → tier={r.actual_tier} score={r.actual_score}")
        if not r.error:
            print(f"       scores  → {r.judge_scores}")
            print(f"       verdict → {r.judge_reasoning}")
    print("=" * 78)

    out_path = os.path.join(os.path.dirname(__file__), "final-report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📝 Full report saved → {out_path}")

if __name__ == "__main__":
    asyncio.run(main())