"""
business_impact_scorer.py — Main business impact scoring powered by local Qwen2.5-Coder
        # FINAL RESEARCH MODEL:
        # Score = Σ w_i x_i
"""

from __future__ import annotations
import json
import httpx
import math
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from models import PRPayload, ImpactTier

@dataclass
class BusinessImpactConfig:
    """Configuration for local model routing parameters"""
    ollama_url: str = "http://127.0.0.1:11434/api/generate"
    model_name: str = "qwen2.5-coder:1.5b"
    model_weight: float = 0.63
    formula_weight: float = 0.37


class BusinessImpactScorer:
    """Scorer utilizing local Qwen2.5-Coder and mathematical rules"""

    def __init__(self, config: Optional[BusinessImpactConfig] = None):
        self.config = config or BusinessImpactConfig()

    def calculate_formula_score(
        self,
        pr: PRPayload,
        blast_score: float,
        user_score: float,
        deadline_score: float,
    ) -> float:
        """Calculate business impact using weighted structural rule heuristics."""
        combined_text = f"{pr.pr_title} {pr.pr_body} {' '.join(pr.changed_files)}".lower()

        component_scores = {
            "payment":  1.0 if any(p in combined_text for p in ["payment", "stripe", "paypal", "charge", "checkout"]) else 0.0,
            "auth":     0.9 if any(p in combined_text for p in ["auth", "login", "password", "token", "jwt"]) else 0.0,
            "database": 0.7 if any(p in combined_text for p in ["database", "migration", "schema"]) else 0.0,
            "api":      0.6 if any(p in combined_text for p in ["api", "endpoint", "route", "controller"]) else 0.0,
        }
        component_crit = max(component_scores.values(), default=0.45)

        security_keywords = ["security", "vulnerability", "exploit", "injection", "xss", "csrf", "bypass",        "authentication",
        "authorization",
        "jwt",
        "oauth",
        "login",
        "password"]
        security_risk = 0.8 if any(k in combined_text for k in security_keywords) else 0.44

        revenue_keywords = ["payment", "billing", "subscription", "invoice", "checkout", "transaction"]
        revenue_impact = 0.9 if any(k in combined_text for k in revenue_keywords) else 0.35

        score = (
            0.25 * component_crit +
            0.25 * user_score +
            0.20 * security_risk +
            0.30 * revenue_impact +
            0.10 * blast_score
        )

        deadline_boost = 1.0 + (deadline_score * 0.35)
        return min(score * deadline_boost, 1.0)

    async def calculate_local_qwen_score(self, pr: PRPayload, reporter_email: str = "") -> Dict[str, Any]:
        """Queries the local qwen2.5-coder:1.5b instance using HTTPX asynchronously."""
        
        jira_context = ""
        for ticket in pr.linked_jira_tickets:
            jira_context += f"- {ticket.key}: {ticket.summary} (Severity: {ticket.severity})\n"
        if not jira_context:
            jira_context = "No linked tickets available."

        # ✅ Added context-resolved dynamic signature tracker mapping line
        prompt = f"""You are a software architect and product owner. Analyze this Pull Request:

PR SUBMITTER PROFILE: {reporter_email if reporter_email else "unknown@domain.internal"}
PR TITLE: {pr.pr_title}
PR DESCRIPTION: {pr.pr_body}
METADATA LABELS: {', '.join(pr.github_labels)}
FILES:
{pr.changed_files}
LINKED JIRA TICKETS:
{jira_context}

Evaluate the systemic danger of this code update. 
Output exactly one valid JSON object. Do not output any markdown text, notes, or backticks.

Expected Schema:
{{
    "business_summary": "...",
    "affected_systems": [" "],
    "customer_impact":0.0-1.0,
    "revenue_impact":0.0-1.0,
    "security_impact":0.0-1.0,
    "deployment_risk":0.0-1.0,
    "ai_risk_score": 0.0-1.0
}}
"""

        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }

        default_fallback = {
            "ai_score": 0.56,
            "summary": "Local engine timeout or processing error.",
            "affected_systems": ["unknown"]
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(self.config.ollama_url, json=payload)
                if response.status_code == 200:
                    raw_data = response.json()
                    model_text = raw_data.get("response", "{}").strip()
                    model_text = model_text.replace("```json", "").replace("```", "").strip()
                    
                    json_match = re.search(r"\{.*\}", model_text, re.DOTALL)
                    if json_match:
                        model_text = json_match.group(0)
                        
                    parsed = json.loads(model_text)
                    ai_score = parsed.get("ai_risk_score", parsed.get("ai_score", 0.5))
                    
                    return {
                        "ai_score": float(ai_score),

                        "customer_impact":
                            float(parsed.get("customer_impact",0.5)),

                        "revenue_impact":
                            float(parsed.get("revenue_impact",0.5)),

                        "security_impact":
                            float(parsed.get("security_impact",0.5)),

                        "deployment_risk":
                            float(parsed.get("deployment_risk",0.5)),

                        "summary":
                            parsed.get("business_summary",""),

                        "affected_systems":
                            parsed.get("affected_systems",[])
                    }
                    
                else:
                    print(f"⚠️ Ollama returned non-200 HTTP response: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Local Qwen lookup skipped or failed: [{type(e).__name__}] -> {e}")
            
        return default_fallback

    async def calculate_business_impact(
        self,
        pr: PRPayload,
        blast_score: float,
        user_score: float,
        deadline_score: float,
        reporter_email: str = ""  # ✅ Param field exposed
    ) -> Dict[str, Any]:
        """Blends the heuristic rules with local AI insights."""
        formula_score = self.calculate_formula_score(pr, blast_score, user_score, deadline_score)
        
        # ✅ Forward live identities directly into local prompt configurations
        ai_result = await self.calculate_local_qwen_score(pr, reporter_email=reporter_email)

        blended_score = (
            (self.config.formula_weight * formula_score) +
            (self.config.model_weight * ai_result["ai_score"])
        )

        return {
            "score": min(max(blended_score, 0.0), 1.0),
            "formula_score": formula_score,
            "llm_score": ai_result["ai_score"],
            "llm_confidence": 1.0,
            "business_summary": ai_result["summary"],
            "affected_systems": ai_result["affected_systems"],
        }


def score_to_tier(score: float) -> ImpactTier:
    """Convert a 0-100 score to an ImpactTier enum."""
    if score >= 70:
        return ImpactTier.HIGH
    elif score >= 40:
        return ImpactTier.MEDIUM
    return ImpactTier.LOW