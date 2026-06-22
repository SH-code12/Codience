import json
import re
from typing import Dict, Any, List

import sys
import os

# Add to sys.path if needed based on structure
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from .llm import generate_with_resilience
from .prompts import JUDGE_EVALUATION_PROMPT

def evaluate_recommendations(pr_data: Dict[str, Any], recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates the proposed recommendations using an LLM-as-a-judge.
    Returns a dict with 'accepted' (bool) and 'feedback' (str).
    """
    if not recommendations:
        return {"accepted": True, "feedback": "No recommendations provided to evaluate."}

    # Format PR Data
    title = pr_data.get("title", "No Title")
    description = pr_data.get("description", "No Description")

    # Format Reviewers
    reviewers_lines = []
    for i, rec in enumerate(recommendations, 1):
        name = rec.get("name", f"Reviewer_{i}")
        score = rec.get("confidence_score", 0)
        justification = rec.get("justification", "No justification")
        reasons = ", ".join(rec.get("reasons", []))
        reviewers_lines.append(
            f"{i}. Name: {name}\n"
            f"   Score: {score}/100\n"
            f"   Justification: {justification}\n"
            f"   Reasons: {reasons}"
        )
    reviewers_text = "\n\n".join(reviewers_lines)

    prompt = JUDGE_EVALUATION_PROMPT.format(
        title=title,
        description=description,
        reviewers_text=reviewers_text
    )

    result = generate_with_resilience(prompt, purpose="evaluator_judge")
    if not result.get("ok"):
        print(f"⚠️ Evaluator LLM failed: {result.get('reason')}")
        # Default to accepted if the judge fails, to avoid breaking the pipeline
        return {"accepted": True, "feedback": f"Judge unavailable: {result.get('reason')}"}

    try:
        cleaned = re.sub(r"```(?:json)?|```", "", result.get("text", "")).strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        parsed = json.loads(match.group() if match else cleaned)
        
        # Depending on the model, boolean might come back as string 'true'/'false'
        raw_accepted = parsed.get("accepted", True)
        if isinstance(raw_accepted, str):
            accepted = raw_accepted.lower() == 'true'
        else:
            accepted = bool(raw_accepted)
            
        feedback = str(parsed.get("feedback", ""))
        
        return {
            "accepted": accepted,
            "feedback": feedback
        }
    except Exception as exc:
        print(f"⚠️ Evaluator parse error: {exc}")
        # Default to accepted if parsing fails
        return {"accepted": True, "feedback": f"Parse error: {exc}"}
