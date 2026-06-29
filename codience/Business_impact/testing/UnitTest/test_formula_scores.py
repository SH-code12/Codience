# Run pytest UnitTest/test_formula_scores.py -v
import sys
import pytest
import math
from datetime import date, timedelta
from pathlib import Path

# Automatically inject the project root into your Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from signal_scorers import score_user_exposure, score_deadline, _kw_bucket
from blast_radius import score_blast_radius, _code_files, _count_routes
from business_impact_scorer import BusinessImpactScorer, score_to_tier
from models import UserExposureBucket, ImpactTier

# --- Signal Scorers Unit Tests ---

def test_kw_bucket_critical():
    bucket, hits = _kw_bucket("This update includes a stripe billing fix.")
    assert bucket == UserExposureBucket.CRITICAL
    assert "stripe" in hits or "billing" in hits

def test_score_user_exposure_calculation(sample_pr_payload):
    result = score_user_exposure(
        sample_pr_payload.pr_title,
        sample_pr_payload.pr_body,
        sample_pr_payload.diff_excerpt,
        sample_pr_payload.linked_jira_tickets
    )
    assert result.bucket == UserExposureBucket.CRITICAL
    assert result.score > 0.0
    # match the actual formula log string output
    assert "15000" in result.explanation

def test_score_deadline_overdue(sample_jira_ticket):
    # Simulate an overdue deadline (Yesterday)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    sample_jira_ticket.sprint_end_date = yesterday
    sample_jira_ticket.milestone_due_date = None
    
    result = score_deadline([sample_jira_ticket], milestone=None)
    # Sigmoid should score overdue tasks higher than 0.5
    assert result.score > 0.5
    assert result.days_remaining == 0  # UI display should clamp to 0

# --- Blast Radius Unit Tests ---

def test_code_files_filtering():
    files = ["test.py", "readme.md", "index.ts", "logo.png"]
    filtered = _code_files(files)
    assert "test.py" in filtered
    assert "index.ts" in filtered
    assert "readme.md" not in filtered

def test_count_routes_regex():
    diff = "+@app.get('/api/v1/users')\n+def get_users():\n+[HttpGet]\n+public IActionResult Get()"
    assert _count_routes(diff) == 2

def test_score_blast_radius_bounds():
    changed_files = ["src/auth.py", "src/db.py"]
    diff = "import jwt\nusing database;"
    result = score_blast_radius(changed_files, diff)
    assert 0.0 <= result.score <= 1.0

# --- Business Impact Scorer Unit Tests ---

def test_calculate_formula_score_weights(sample_pr_payload):
    scorer = BusinessImpactScorer()
    score = scorer.calculate_formula_score(
        pr=sample_pr_payload,
        blast_score=0.5,
        user_score=0.9,
        deadline_score=0.2
    )
    assert 0.0 <= score <= 1.0

def test_score_to_tier_mapping():
    assert score_to_tier(85.0) == ImpactTier.HIGH
    assert score_to_tier(55.0) == ImpactTier.MEDIUM
    assert score_to_tier(20.0) == ImpactTier.LOW