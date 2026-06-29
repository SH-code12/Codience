# pytest APITest/test_api.py -v
import sys
import pytest
import os
from pathlib import Path

# Inject project root into execution path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Mock required environment variables BEFORE importing the app to avoid system exits
os.environ["GITHUB_TOKEN"] = "mock-github-token"
os.environ["DOTNET_API_URL"] = "http://127.0.0.1:5051"

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from main import app
from models import ImpactTier

# Initialize the TestClient with lifespan validation deactivated
client = TestClient(app, raise_server_exceptions=False)

# ==========================================
# /api/rank/pr/{owner}/{repo}/{pr_number} Tests
# ==========================================

@patch("main.pr_fetcher")
@patch("main.ranking_engine.score_single_pr", new_callable=AsyncMock)
def test_rank_single_pr_by_id_success(mock_score_single, mock_fetcher_instance):
    mock_raw_pr = MagicMock()
    mock_fetcher_instance.github.get_pull_request.return_value = mock_raw_pr
    mock_fetcher_instance._github_pr_to_dict.return_value = {}
    mock_fetcher_instance.pr_enricher.enrich_pr_with_jira.return_value = {}
    mock_fetcher_instance._dict_to_pr_payload.return_value = MagicMock()
    
    mock_score_res = MagicMock()
    mock_score_res.pr_number = 10
    mock_score_res.pr_title = "fix(auth): secure tokens"
    mock_score_res.weighted_score = 45.0
    mock_score_res.tier.value = "medium"
    mock_score_res.should_block_merge = False
    mock_score_res.blast_radius.score = 0.3
    mock_score_res.user_exposure.score = 0.5
    mock_score_res.deadline.score = 0.1
    mock_score_res.llm_semantic.business_summary = "Minor authentication fix."
    mock_score_res.llm_semantic.raw_score = 0.4
    mock_score_res.score_breakdown = {"formula_score": 0.42}
    
    mock_score_single.return_value = mock_score_res

    response = client.get("/api/rank/pr/Codience/Codience-Core/10")
    
    assert response.status_code == 200
    data = response.json()
    assert data["pr_number"] == 10
    assert data["weighted_score"] == 45.0
    assert data["tier"] == "medium"
    assert data["score_breakdown"]["formula_score"] == 0.42


@patch("main.pr_fetcher")
def test_rank_single_pr_by_id_not_found(mock_fetcher_instance):
    mock_fetcher_instance.github.get_pull_request.side_effect = Exception("Not found")
    
    response = client.get("/api/rank/pr/Codience/Codience-Core/999")
    assert response.status_code == 404


# ==========================================
# /api/rank/pr/{owner}/{repo}/{pr_number}/with-config Tests
# ==========================================

@patch("main.pr_fetcher")
@patch("main.ranking_engine.score_single_pr", new_callable=AsyncMock)
def test_rank_single_pr_with_explicit_config_success(mock_score_single, mock_fetcher_instance):
    mock_fetcher_instance.github.get_pull_request.return_value = MagicMock()
    mock_fetcher_instance._github_pr_to_dict.return_value = {}
    mock_fetcher_instance.pr_enricher.enrich_pr_with_explicit_jira_config.return_value = {}
    mock_fetcher_instance._dict_to_pr_payload.return_value = MagicMock()

    mock_score_res = MagicMock()
    mock_score_res.pr_number = 12
    mock_score_res.pr_title = "refactor: clean database layer"
    mock_score_res.weighted_score = 72.5
    mock_score_res.tier.value = "high"
    mock_score_res.should_block_merge = True
    mock_score_res.blast_radius.score = 0.8
    mock_score_res.user_exposure.score = 0.7
    mock_score_res.deadline.score = 0.6
    mock_score_res.llm_semantic.business_summary = "High risk migration modification configuration."
    mock_score_res.llm_semantic.raw_score = 0.75
    mock_score_res.score_breakdown = {"formula_score": 0.68}
    
    mock_score_single.return_value = mock_score_res

    config_payload = {
        "jira_api_token": "test-token-123",
        "jira_cloud_id": "test-cloud-id",
        "jira_project_key": "PROJ"
    }

    response = client.post("/api/rank/pr/Codience/Codience-Core/12/with-config", json=config_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["weighted_score"] == 72.5
    assert data["should_block_merge"] is True


def test_rank_single_pr_with_explicit_config_validation_error():
    response = client.post("/api/rank/pr/Codience/Codience-Core/12/with-config", json={})
    assert response.status_code == 422