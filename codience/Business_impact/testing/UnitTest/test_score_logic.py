# Run pytest UnitTest/test_score_logic.py -v

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Mimic the import paths structure from your sample setup
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from business_impact_scorer import BusinessImpactScorer, score_to_tier
from models import PRPayload, JiraTicket, ImpactTier, UserExposureBucket

@pytest.fixture
def scorer():
    """Returns a baseline BusinessImpactScorer instance for heuristic testing."""
    return BusinessImpactScorer()

@pytest.fixture
def base_pr():
    """Generates a minimal baseline PR payload struct."""
    return PRPayload(
        pr_number=101,
        pr_title="minor formatting changes",
        pr_body="Cleaned up trailing white spaces.",
        repo_owner="Codience",
        repo_name="Codience-Core",
        changed_files=["utils.py"]
    )

# ==========================================
# Rule Engine Heuristic Feature Tests
# ==========================================

def test_calculate_formula_score_component_weights(scorer, base_pr):
    # Test high-criticality path triggers (Payment keywords)
    base_pr.pr_title = "feat: implement stripe billing callback loop"
    score_high = scorer.calculate_formula_score(
        pr=base_pr, blast_score=0.2, user_score=0.5, deadline_score=0.0
    )
    
    # Test normal code modification path trigger
    base_pr.pr_title = "docs: update contribution guidelines"
    score_low = scorer.calculate_formula_score(
        pr=base_pr, blast_score=0.2, user_score=0.5, deadline_score=0.0
    )
    
    assert score_high > score_low


def test_calculate_formula_score_deadline_boost(scorer, base_pr):
    # High pressure deadline impact factor evaluation
    score_boosted = scorer.calculate_formula_score(
        pr=base_pr, blast_score=0.1, user_score=0.1, deadline_score=1.0
    )
    score_normal = scorer.calculate_formula_score(
        pr=base_pr, blast_score=0.1, user_score=0.1, deadline_score=0.0
    )
    
    assert score_boosted > score_normal
    assert score_boosted <= 1.0  # Verify clamping boundary logic holding up


def test_score_to_tier_mapping():
    assert score_to_tier(89.5) == ImpactTier.HIGH
    assert score_to_tier(55.0) == ImpactTier.MEDIUM
    assert score_to_tier(12.0) == ImpactTier.LOW