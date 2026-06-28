import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from codience.src.Reviewer_Recommender.PRNew.Reviewer_Engine import ReviewerRecommender

@pytest.fixture
def engine():
    # using mocks reviewerw
    return ReviewerRecommender(owner="mock", repo="mock")

def test_parse_commit_datetime(engine):
    date_str = "2023-10-01T12:00:00Z"
    parsed = engine._parse_commit_datetime(date_str)
    assert parsed is not None
    assert parsed.year == 2023
    assert parsed.month == 10
    
    assert engine._parse_commit_datetime("invalid-date") is None
    assert engine._parse_commit_datetime(None) is None

def test_build_contributor_stats(engine):
    # We dynamically generate dates relative to "now" to test recency scoring
    now = datetime.now(timezone.utc)
    date_45_days_ago = (now - timedelta(days=45)).isoformat()
    date_180_days_ago = (now - timedelta(days=180)).isoformat()
    
    custom_commits = [
        {
            "author": {"login": "dev_recent"},
            "commit": {"author": {"name": "dev_recent", "date": date_45_days_ago}},
            "files": [{"filename": "src/auth.py"}],
            "sha": "abc1"
        },
        {
            "author": {"login": "dev_old"},
            "commit": {"author": {"name": "dev_old", "date": date_180_days_ago}},
            "files": [{"filename": "src/utils.py"}],
            "sha": "def2"
        }
    ]
    
    stats = engine._build_contributor_stats(custom_commits)
    
    assert "dev_recent" in stats
    assert "dev_old" in stats
    
    # dev_recent was 45 days ago. Score formula: 1.0 - (min(recency_days, 90) / 90.0)
    # 1.0 - (45/90) = 0.5
    assert stats["dev_recent"]["recency_score"] == 0.5
    
    # dev_old was 180 days ago (exceeds 90 days threshold). Score should be 0.0
    assert stats["dev_old"]["recency_score"] == 0.0

def test_limit_commits_per_reviewer(engine, mock_commits):
    # Limit to 1 commit per reviewer
    limited = engine._limit_commits_per_reviewer(mock_commits, 1)
    
    # Should only have 1 for dev1, 1 for dev2 = 2 total
    assert len(limited) == 2
    
    dev1_commits = [c for c in limited if c["author"]["login"] == "dev1"]
    assert len(dev1_commits) == 1

def test_normalize_required_reviewers(engine):
    required = ["dev1", {"username": "dev2", "raw_skills": ["Python"]}]
    
    normalized = engine._normalize_required_reviewers(required)
    
    assert "dev1" in normalized
    assert normalized["dev1"]["username"] == "dev1"
    
    assert "dev2" in normalized
    assert normalized["dev2"]["username"] == "dev2"
    assert "Python" in normalized["dev2"]["raw_skills"]