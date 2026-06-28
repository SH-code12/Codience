import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from codience.src.app import app

client = TestClient(app)

# ==========================================
# /api/analyze/jira-tickets Tests
# ==========================================

@patch("codience.src.app.analyze_jira_tickets")
def test_analyze_jira_tickets_success(mock_analyze):
    mock_analyze.return_value = {"PROJ-123": {"summary": "Test ticket", "components": []}}
    response = client.post("/api/analyze/jira-tickets", json={
        "username": "testuser",
        "tickets": ["PROJ-123"]
    })
    assert response.status_code == 200
    assert response.json() == {"PROJ-123": {"summary": "Test ticket", "components": []}}

def test_analyze_jira_tickets_validation_error():
    # Missing required field 'username'
    response = client.post("/api/analyze/jira-tickets", json={
        "tickets": ["PROJ-123"]
    })
    assert response.status_code == 422

@patch("codience.src.app.analyze_jira_tickets")
def test_analyze_jira_tickets_empty_list(mock_analyze):
    mock_analyze.return_value = {}
    response = client.post("/api/analyze/jira-tickets", json={
        "username": "testuser",
        "tickets": []
    })
    assert response.status_code == 200
    assert response.json() == {}

# ==========================================
# /api/analyze/commit-history Tests
# ==========================================

@patch("codience.src.app.map_commits_to_skills")
def test_analyze_commit_history_success(mock_map_commits):
    mock_map_commits.return_value = {"testauthor": {"Python", "FastAPI"}}
    response = client.post("/api/analyze/commit-history", json={
        "author": "testauthor",
        "commits": ["sha123"]
    })
    assert response.status_code == 200
    assert set(response.json()["skills"]) == {"Python", "FastAPI"}

def test_analyze_commit_history_validation_error():
    # Missing 'commits' field
    response = client.post("/api/analyze/commit-history", json={
        "author": "testauthor"
    })
    assert response.status_code == 422

@patch("codience.src.app.map_commits_to_skills")
def test_analyze_commit_history_empty_list(mock_map_commits):
    mock_map_commits.return_value = {}
    response = client.post("/api/analyze/commit-history", json={
        "author": "testauthor",
        "commits": []
    })
    assert response.status_code == 200
    assert response.json()["skills"] == []

# ==========================================
# /api/recommend/reviewer Tests
# ==========================================

@patch("codience.src.app.get_composite_recommendations")
def test_recommend_reviewer_success(mock_get_composite):
    mock_get_composite.return_value = [
        {"name": "reviewer1", "confidence_score": 90, "justification": "Good"},
        {"name": "reviewer2", "confidence_score": 80, "justification": "Okay"}
    ]
    response = client.post("/api/recommend/reviewer", json={
        "pr_data": {"files": [], "commits": []},
        "candidates": [{"name": "reviewer1"}, {"name": "reviewer2"}],
        "options": {}
    })
    assert response.status_code == 200
    assert "recommended_reviewers" in response.json()
    assert len(response.json()["recommended_reviewers"]) == 2

def test_recommend_reviewer_validation_error():
    # Missing 'pr_data' field
    response = client.post("/api/recommend/reviewer", json={
        "candidates": [{"name": "reviewer1"}],
        "options": {}
    })
    assert response.status_code == 422

# ==========================================
# /api/recommend-reviewers Tests
# ==========================================

@patch("codience.src.app.get_pr_data_or_raise")
@patch("codience.src.app._build_engine")
def test_recommend_reviewers_default_engine(mock_build_engine, mock_get_pr_data):
    mock_get_pr_data.return_value = {"diff": "some diff"}
    
    mock_engine = MagicMock()
    mock_engine.recommend_v2.return_value = {
        "recommended_reviewers": [{"name": "dev1", "confidence_score": 95, "justification": "Expert"}]
    }
    mock_build_engine.return_value = mock_engine

    response = client.post("/api/recommend-reviewers", json={
        "owner": "org",
        "repo": "repo",
        "pr_number": 1
    })
    
    assert response.status_code == 200
    assert len(response.json()["recommended_reviewers"]) == 1
    mock_build_engine.assert_called_once()
    mock_engine.recommend_v2.assert_called_once()

@patch("codience.src.app.get_pr_data_or_raise")
@patch("codience.src.app._build_engine_for_required")
def test_recommend_reviewers_required_engine(mock_build_required, mock_get_pr_data):
    mock_get_pr_data.return_value = {"diff": "some diff"}
    
    mock_engine = MagicMock()
    mock_engine.recommend_v2.return_value = {
        "recommended_reviewers": [{"name": "req_dev", "confidence_score": 85, "justification": "Required"}]
    }
    mock_build_required.return_value = mock_engine

    response = client.post("/api/recommend-reviewers", json={
        "owner": "org",
        "repo": "repo",
        "pr_number": 1,
        "required_reviewers": ["req_dev"]
    })
    
    assert response.status_code == 200
    assert response.json()["recommended_reviewers"][0]["name"] == "req_dev"
    mock_build_required.assert_called_once()

def test_recommend_reviewers_validation_error():
    # Missing repo, owner, pr_number
    response = client.post("/api/recommend-reviewers", json={})
    assert response.status_code == 422

# ==========================================
# /api/orchestrator Tests
# ==========================================

@patch("codience.src.app.get_pr_data_or_raise")
@patch("codience.src.app.ReviewerRecommender")
@patch("codience.src.app._profile_single_user")
@patch("codience.src.app.get_composite_recommendations")
def test_orchestrator_success(mock_get_composite, mock_profile, mock_recommender, mock_get_pr_data):
    mock_get_pr_data.return_value = {"diff": "diff data"}
    mock_profile.side_effect = [{"name": "userA"}, {"name": "userB"}]
    mock_get_composite.return_value = [
        {"name": "userA", "confidence_score": 90, "justification": "Match"},
        {"name": "userB", "confidence_score": 80, "justification": "Match"}
    ]

    response = client.post("/api/orchestrator", json={
        "owner": "org",
        "repo": "repo",
        "pr_number": 123,
        "users": [
            {"github_username": "userA"},
            {"github_username": "userB"}
        ]
    })

    assert response.status_code == 200
    assert len(response.json()["recommended_reviewers"]) == 2
    assert mock_profile.call_count == 2
    mock_get_composite.assert_called_once()

@patch("codience.src.app.get_pr_data_or_raise")
@patch("codience.src.app.ReviewerRecommender")
@patch("codience.src.app.get_composite_recommendations")
def test_orchestrator_empty_users(mock_get_composite, mock_recommender, mock_get_pr_data):
    mock_get_pr_data.return_value = {"diff": "diff data"}
    mock_get_composite.return_value = []

    response = client.post("/api/orchestrator", json={
        "owner": "org",
        "repo": "repo",
        "pr_number": 123,
        "users": []
    })

    assert response.status_code == 200
    assert response.json()["recommended_reviewers"] == []
    mock_get_composite.assert_called_once()

def test_orchestrator_validation_error():
    # Missing 'users' field
    response = client.post("/api/orchestrator", json={
        "owner": "org",
        "repo": "repo",
        "pr_number": 123
    })
    assert response.status_code == 422
