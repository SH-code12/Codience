import sys
import pytest
import asyncio
from pathlib import Path

# Automatically inject the project root into your Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import PRPayload, JiraTicket

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_jira_ticket():
    return JiraTicket(
        key="PROJ-123",
        summary="Fix critical stripe payment gateway processing timeout loop",
        severity="Critical",
        priority="high",
        labels=["payment", "blocking-bug"],
        affected_users_count=15000,
        sprint_end_date="2026-07-15T23:59:59Z",
        milestone_due_date="2026-08-01T00:00:00Z",
        description="Users experiencing latency drops during checkout steps.",
        status="In Progress"
    )

@pytest.fixture
def sample_pr_payload(sample_jira_ticket):
    return PRPayload(
        pr_number=42,
        pr_title="feat(payment): integrate stripe payment pipeline backend",
        pr_body="Resolves timeout exceptions when checking out.",
        repo_owner="Codience-Engine",
        repo_name="impact-ranker",
        head_branch="feature/stripe-fix",
        base_branch="main",
        diff_excerpt="diff --git a/payment.py b/payment.py\n+import stripe\n+@router.post('/checkout')\n+def process(): pass",
        changed_files=["src/controllers/payment.py", "src/models/schema.sql"],
        github_labels=["bug", "high-priority"],
        milestone_due_date="2026-08-01T00:00:00Z",
        linked_jira_tickets=[sample_jira_ticket]
    )