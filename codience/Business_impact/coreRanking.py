"""
coreRank.py — Core engine orchestrating code metrics and local AI analysis
"""

import asyncio
import time
from typing import List
from models import PRPayload, PRScoreResult, RankedPRList, ImpactTier, LLMSemanticDetail
from blast_radius import score_blast_radius
from signal_scorers import score_user_exposure, score_deadline
from business_impact_scorer import BusinessImpactScorer, score_to_tier

class PRRankingEngine:
    """Engine for ranking pull requests using completely local models"""
    
    def __init__(self):
        self.business_scorer = BusinessImpactScorer()
    
    async def score_single_pr(self, pr: PRPayload, reporter_email: str = "") -> PRScoreResult:
        """Score a single pull request payload with context-infused tracking properties"""
        start_time = time.time()
        
        # Calculate heuristics
        blast = score_blast_radius(pr.changed_files, pr.diff_excerpt)
        user = score_user_exposure(pr.pr_title, pr.pr_body, pr.diff_excerpt, pr.linked_jira_tickets)
        deadline = score_deadline(pr.linked_jira_tickets, pr.milestone_due_date)
        
        # ✅ Fixed signature mismatch by forwarding optional context string block parameters
        business_impact = await self.business_scorer.calculate_business_impact(
            pr, blast.score, user.score, deadline.score, reporter_email=reporter_email
        )
        
        weighted_score = business_impact['score'] * 100
        
        llm_semantic = LLMSemanticDetail(
            business_summary=business_impact.get('business_summary', ''),
            affected_systems=business_impact.get('affected_systems', []),
            user_impact_bucket=user.bucket,
            raw_score=business_impact.get('llm_score', 0.5),
            confidence=1.0,
            final_score=business_impact.get('llm_score', 0.5),
            model_used="qwen2.5-coder:1.5b"
        )
        
        should_block = (
            weighted_score >= 80 or
            user.bucket.value == "critical" or
            any(t.severity.lower() == "blocker" for t in pr.linked_jira_tickets)
        )
        
        comment = self._generate_github_comment(pr, weighted_score, business_impact, should_block)
        processing_ms = int((time.time() - start_time) * 1000)
        
        return PRScoreResult(
            pr_number=pr.pr_number,
            pr_title=pr.pr_title,
            repo=f"{pr.repo_owner}/{pr.repo_name}",
            blast_radius=blast,
            user_exposure=user,
            deadline=deadline,
            llm_semantic=llm_semantic,
            weighted_score=weighted_score,
            tier=score_to_tier(weighted_score),
            score_breakdown={
                'blast_radius': blast.score,
                'user_exposure': user.score,
                'deadline': deadline.score,
                'business_impact': business_impact['score'],
                'formula_score': business_impact.get('formula_score', 0),
                'local_model_score': business_impact.get('llm_score', 0)
            },
            recommended_reviewers=3 if weighted_score >= 70 else 2,
            should_block_merge=should_block,
            github_comment_markdown=comment,
            processing_ms=processing_ms
        )
    
    async def rank_prs(self, prs: List[PRPayload]) -> RankedPRList:
        """Rank multiple pull requests concurrently"""
        tasks = [self.score_single_pr(pr) for pr in prs]
        scored_prs = await asyncio.gather(*tasks)
        
        ranked = sorted(scored_prs, key=lambda x: x.weighted_score, reverse=True)
        
        return RankedPRList(
            total=len(ranked),
            ranked=ranked,
            high_count=sum(1 for r in ranked if r.tier == ImpactTier.HIGH),
            medium_count=sum(1 for r in ranked if r.tier == ImpactTier.MEDIUM),
            low_count=sum(1 for r in ranked if r.tier == ImpactTier.LOW)
        )
    
    def _generate_github_comment(self, pr: PRPayload, score: float, 
                                 business_impact: dict, should_block: bool) -> str:
        """Generates clear production reports markdown format"""
        tier_emoji = "🔴" if score >= 70 else "🟡" if score >= 40 else "🟢"
        block_warning = "⚠️ **CRITICAL: High risk parameters met. Verification required.** ⚠️" if should_block else ""
        
        return f"""## 📊 Business Impact Assessment (Local Core AI Engine)

{tier_emoji} **Impact Score: {score:.1f}/100** - {score_to_tier(score).value.upper()}

{block_warning}

### Metric Specifications:
- **Rule Engine Score:** {business_impact.get('formula_score', 0):.2f}
- **Local Qwen Analysis Score:** {business_impact.get('llm_score', 0):.2f}

### Functional Summary:
{business_impact.get('business_summary', 'No summary generated.')}

### Systems Tagged for Scope Verification:
{', '.join(business_impact.get('affected_systems', ['None Identified']))}

---
*_Report generated securely via local inference machine framework._*
"""