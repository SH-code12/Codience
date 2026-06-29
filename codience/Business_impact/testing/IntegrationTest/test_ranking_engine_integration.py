#  pytest IntegrationTest/test_ranking_engine_integration.py -v
import sys
import pytest
from pathlib import Path

# Automatically inject the project root into your Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coreRanking import PRRankingEngine
from models import PRPayload

def test_ranking_engine_initialization():
    engine = PRRankingEngine()
    assert engine.business_scorer is not None


@pytest.mark.asyncio
async def test_ranking_engine_empty_batch_fallback():
    engine = PRRankingEngine()
    
    # Verify processing safety loop configurations with blank matrix shapes
    result = await engine.rank_prs([])
    
    assert result.total == 0
    assert isinstance(result.ranked, list)
    assert result.high_count == 0
    assert result.medium_count == 0
    assert result.low_count == 0


@pytest.mark.asyncio
async def test_ranking_engine_sorting_order_descending():
    engine = PRRankingEngine()
    
    # Simple explicit inline validation metrics mock
    pr_low = PRPayload(pr_number=1, pr_title="chore: bump version", repo_owner="O", repo_name="R")
    pr_high = PRPayload(pr_number=2, pr_title="CRITICAL security token fix", repo_owner="O", repo_name="R")
    
    batch = [pr_low, pr_high]
    result = await engine.rank_prs(batch)
    
    assert result.total == 2
    # The highest weighted calculation result must cascade to element index 0
    assert result.ranked[0].weighted_score >= result.ranked[1].weighted_score