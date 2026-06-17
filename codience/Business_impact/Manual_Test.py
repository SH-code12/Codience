"""
test_ranking.py - Comprehensive test suite utilizing local qwen2.5-coder via Ollama
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

# Ensure the local directory is in the path
sys.path.insert(0, str(Path(__file__).parent))

from models import (
    PRPayload, JiraTicket, ImpactTier, UserExposureBucket
)
from codience.Business_impact.coreRanking import PRRankingEngine

def create_test_prs() -> List[PRPayload]:
    """
    Creates realistic test PRs mapping out critical, major, and minor changes
    to validate the local Qwen model and rule heuristics.
    """
    
    def jira_ticket(key: str, summary: str, severity: str, priority: str, 
                    users: int = None, days_to_deadline: int = None) -> JiraTicket:
        due_date = None
        if days_to_deadline is not None:
            due_date = (datetime.now() + timedelta(days=days_to_deadline)).isoformat()
        
        return JiraTicket(
            key=key,
            summary=summary,
            severity=severity,
            priority=priority,
            labels=[],
            affected_users_count=users,
            sprint_end_date=due_date,
            milestone_due_date=None,
            description="System generated testing context.",
            status="In Progress"
        )
    
    # PR 1: Critical payment fix with high business impact
    pr1 = PRPayload(
        pr_number=1001,
        pr_title="Fix payment gateway timeout causing transaction failures",
        pr_body="Increases Stripe timeout from 5s to 30s and adds retry logic for failed payments",
        repo_owner="ecommerce",
        repo_name="payment-service",
        head_branch="fix/payment-timeout",
        base_branch="main",
        diff_excerpt="""
+    def process_payment(self, amount, payment_method):
+        stripe.api_key = settings.STRIPE_SECRET_KEY
+        try:
+            charge = stripe.Charge.create(
+                amount=amount,
+                currency='usd',
+                source=payment_method,
+                timeout=30  # Increased from 5 seconds
+            )
+            return charge
+        except stripe.error.TimeoutError:
+            time.sleep(2)
+            return self.retry_payment(amount, payment_method)
        """,
        changed_files=["payment/processor.py", "payment/gateway.py", "config/settings.py"],
        github_labels=["bug", "critical", "payment"],
        linked_jira_tickets=[
            jira_ticket("PAY-123", "Payment timeout causing revenue loss", 
                       "critical", "high", users=15000, days_to_deadline=0)
        ]
    )
    
    # PR 2: Security fix for authentication
    pr2 = PRPayload(
        pr_number=1002,
        pr_title="Fix JWT token validation vulnerability",
        pr_body="Adds proper signature verification for JWT tokens to prevent unauthorized access",
        repo_owner="ecommerce",
        repo_name="auth-service",
        head_branch="fix/jwt-validation",
        base_branch="main",
        diff_excerpt="""
+    def verify_token(self, token):
+        try:
+            decoded = jwt.decode(
+                token, 
+                self.secret_key, 
+                algorithms=['HS256'],
+                verify_signature=True  # Critical security fix
+            )
+            return decoded
+        except jwt.InvalidSignatureError:
+            raise AuthenticationError("Invalid token signature")
        """,
        changed_files=["auth/jwt_handler.py", "auth/middleware.py"],
        github_labels=["security", "critical", "auth"],
        linked_jira_tickets=[
            jira_ticket("SEC-456", "JWT validation bypass vulnerability", 
                       "critical", "urgent", users=50000, days_to_deadline=2)
        ]
    )
    
    # PR 3: Database migration (medium impact)
    pr3 = PRPayload(
        pr_number=1003,
        pr_title="Add user preferences table",
        pr_body="Creates new table for storing user preferences and notification settings",
        repo_owner="ecommerce",
        repo_name="user-service",
        head_branch="feature/user-preferences",
        base_branch="main",
        diff_excerpt="""
+CREATE TABLE user_preferences (
+    user_id INT PRIMARY KEY,
+    notification_enabled BOOLEAN DEFAULT true,
+    theme VARCHAR(50) DEFAULT 'light',
+    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
+);
+ALTER TABLE users ADD COLUMN last_login_ip VARCHAR(45);
        """,
        changed_files=["db/migrations/20240101_add_user_preferences.sql", "models/user.py"],
        github_labels=["feature", "database"],
        linked_jira_tickets=[
            jira_ticket("USER-789", "Store user preferences", 
                       "major", "medium", users=25000, days_to_deadline=7)
        ]
    )
    
    # PR 4: UI component update (low impact)
    pr4 = PRPayload(
        pr_number=1004,
        pr_title="Update button styles on dashboard",
        pr_body="Changes button colors from blue to green for better contrast",
        repo_owner="ecommerce",
        repo_name="frontend",
        head_branch="ui/button-styles",
        base_branch="main",
        diff_excerpt="""
-.btn-primary { background-color: #007bff; }
+.btn-primary { background-color: #28a745; }
        """,
        changed_files=["static/css/buttons.css", "templates/dashboard.html"],
        github_labels=["ui", "style", "enhancement"],
        linked_jira_tickets=[
            jira_ticket("UI-101", "Update dashboard styling", 
                       "minor", "low", users=5000, days_to_deadline=14)
        ]
    )
    
    # PR 5: Documentation update (very low impact)
    pr5 = PRPayload(
        pr_number=1005,
        pr_title="Update README with setup instructions",
        pr_body="Adds detailed setup guide for new developers",
        repo_owner="ecommerce",
        repo_name="docs",
        head_branch="docs/update-readme",
        base_branch="main",
        diff_excerpt="""
+## Local Development Setup
+1. Clone the repository
+2. Run `docker-compose up -d`
        """,
        changed_files=["README.md", "docs/setup.md"],
        github_labels=["documentation", "chore"],
        linked_jira_tickets=[
            jira_ticket("DOC-202", "Improve developer documentation", 
                       "trivial", "low", users=100, days_to_deadline=30)
        ]
    )
    
    return [pr1, pr2, pr3, pr4, pr5]


def print_summary_insights(ranked_results: list):
    """Prints out clear metrics, warnings, and distribution logs."""
    print(f"\n{'='*80}\n💡 SUGGESTED ACTION QUEUE\n{'='*80}")
    
    high = [r for r in ranked_results if r.tier == ImpactTier.HIGH]
    blocked = [r for r in ranked_results if r.should_block_merge]
    
    if high:
        print("\n🚨 URGENT REVIEW REQUIRED (HIGH IMPACT):")
        for r in high:
            print(f"  • [Score: {r.weighted_score:.1f}] PR #{r.pr_number}: {r.pr_title}")
            
    if blocked:
        print("\n⛔ MERGE LOCKOUT TRIGGERED (Requires override/approval):")
        for r in blocked:
            print(f"  • PR #{r.pr_number} | Reason: System block or critical exposure path.")

    print(f"\n📊 Impact Level Split:")
    total = len(ranked_results)
    print(f"  🔴 HIGH:   {len(high)} ({len(high)/total*100:.0f}%)")
    print(f"  🟡 MEDIUM: {sum(1 for r in ranked_results if r.tier == ImpactTier.MEDIUM)} PRs")
    print(f"  🟢 LOW:    {sum(1 for r in ranked_results if r.tier == ImpactTier.LOW)} PRs")


async def main():
    print("=" * 80)
    print("🚀 PR BUSINESS IMPACT RANKING SYSTEM - LOCAL OLLAMA TEST CORE")
    print("=" * 80)
    print("⚡ AI Engine target model: qwen2.5-coder:1.5b (Local via Localhost)")
    
    print("\n📝 Loading target test structures...")
    test_prs = create_test_prs()
    print(f"   ✓ Extracted {len(test_prs)} distinct scenario test vectors.")
    
    print("\n🔧 Initializing runtime ranking engine...")
    engine = PRRankingEngine()
    
    print("\n🎯 Routing payloads to local analysis pipeline...")
    # Leveraging the engine's batch pipeline tool directly
    ranked_payload = await engine.rank_prs(test_prs)
    
    print(f"\n{'='*80}\n📋 RUNTIME EXECUTION PRINTOUT\n{'='*80}")
    for idx, result in enumerate(ranked_payload.ranked, 1):
        print(f"\n{idx}. PR #{result.pr_number}: {result.pr_title}")
        print(f"   Score: {result.weighted_score:.1f}/100 | Tier: {result.tier.value.upper()}")
        print(f"   Reviewers Assigned: {result.recommended_reviewers} | Blocked: {result.should_block_merge}")
        print(f"   AI Summary Insight: {result.llm_semantic.business_summary}")
        print(f"   Affected Components Found by AI: {result.llm_semantic.affected_systems}")
        print("-" * 50)
        
    # Output insights block
    print_summary_insights(ranked_payload.ranked)
    
    # Dump evaluation snapshot directly to local space
    output_file = Path(__file__).parent / "test_results.json"
    serializable_data = [
        {
            "pr_number": pr.pr_number,
            "pr_title": pr.pr_title,
            "weighted_score": pr.weighted_score,
            "tier": pr.tier.value,
            "should_block_merge": pr.should_block_merge,
            "recommended_reviewers": pr.recommended_reviewers,
            "ai_summary": pr.llm_semantic.business_summary,
            "score_breakdown": pr.score_breakdown
        }
        for pr in ranked_payload.ranked
    ]
    
    with open(output_file, 'w') as f:
        json.dump(serializable_data, f, indent=2)
        
    print(f"\n💾 Validation schema saved successfully to: {output_file}")
    print("✅ Testing round successfully terminated.")


if __name__ == "__main__":
    asyncio.run(main())