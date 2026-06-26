import pytest
from codience.src.Reviewer_Recommender.PRNew.Reviewer_Engine import ReviewerRecommender

def test_engine_initialization():
    engine = ReviewerRecommender(owner="test_owner", repo="test_repo")
    assert engine.owner == "test_owner"
    assert engine.repo == "test_repo"

def test_engine_recommend_v2_empty_pr():
    engine = ReviewerRecommender(owner="test_owner", repo="test_repo")
    pr_data = {
        "files": [],
        "commits": []
    }
    
    result = engine.recommend_v2(
        pr_data=pr_data,
        required_reviewers=[],
        options={},
    )
    
    assert "recommended_reviewers" in result
    assert isinstance(result["recommended_reviewers"], list)
