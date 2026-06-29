# pytest IntegrationTest/test_orchestration_fallbacks.py -v
import sys
import pytest
from pathlib import Path

# Automatically inject the project root into your Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unittest.mock import AsyncMock, MagicMock, patch
from coreRanking import PRRankingEngine
from dotnet_jira_client import PRJiraEnricher
from business_impact_scorer import BusinessImpactScorer

@pytest.mark.asyncio
async def test_ranking_engine_orchestration(sample_pr_payload):
    engine = PRRankingEngine()
    
    # Mock the LLM scorer to bypass network requirements during execution
    mock_llm_response = {
        "score": 0.75,
        "formula_score": 0.65,
        "llm_score": 0.80,
        "llm_confidence": 1.0,
        "business_summary": "Verified core systems change.",
        "affected_systems": ["payment", "gateway"]
    }
    
    with patch.object(BusinessImpactScorer, 'calculate_business_impact', new_callable=AsyncMock) as mock_calculate:
        mock_calculate.return_value = mock_llm_response
        result = await engine.score_single_pr(sample_pr_payload, reporter_email="shahd@domain.com")
        
        assert result.pr_number == sample_pr_payload.pr_number
        assert result.weighted_score == 75.0
        assert result.should_block_merge is True  # Score >= 70 triggers High Impact actions
    assert "payment" in result.llm_semantic.affected_systems
def test_pr_jira_enricher_extraction():
    enricher = PRJiraEnricher()
    title = "FIX [PROJ-999] and [CORE-123] validation faults"
    keys = enricher.extract_jira_keys_from_pr(title, pr_body="", branch_name="", labels=[])
    assert "PROJ-999" in keys
    assert "CORE-123" in keys

@pytest.mark.asyncio
async def test_local_qwen_scorer_fallback():
    scorer = BusinessImpactScorer()
    # Execute with invalid target endpoint to force verification of recovery loops
    scorer.config.ollama_url = "http://127.0.0.1:9999/invalid-endpoint"
    
    with patch('httpx.AsyncClient.post', side_effect=Exception("Connection refused")):
        res = await scorer.calculate_local_qwen_score(MagicMock())
        assert res["ai_score"] == 0.56  # Production recovery value matches
        assert "timeout" in res["summary"].lower()