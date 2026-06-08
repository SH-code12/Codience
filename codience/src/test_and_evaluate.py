import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import numpy as np

# Import the FastAPI application
from codience.src.app import app
from codience.src.models import RecommendReviewersRequest

client = TestClient(app)

# =====================================================================
# PART 1: API UNIT TESTS (FastAPI TestClient)
# =====================================================================

class TestReviewerRecommenderAPI(unittest.TestCase):
    
    @patch("codience.src.helpers.fetch_real_pr_data")
    @patch("codience.src.helpers.ReviewerRecommender")
    def test_recommend_reviewers_endpoint(self, mock_recommender_class, mock_fetch_pr):
        """Test the main /api/recommend-reviewers endpoint with mocked dependencies."""
        # 1. Mock PR Data
        mock_fetch_pr.return_value = {
            "title": "Fix memory leak in trainer",
            "description": "Optimized memory footprint",
            "files": [{"filename": "src/trainer.py", "patch": "+ def optimize(): pass"}]
        }
        
        # 2. Mock Recommender Engine behavior
        mock_engine = MagicMock()
        mock_recommender_class.return_value = mock_engine
        mock_engine.recommend_v2.return_value = {
            "recommended_reviewers": [
                {"name": "ArthurZucker", "confidence_score": 90, "justification": "Expert in training loop"},
                {"name": "younesbelkada", "confidence_score": 75, "justification": "Maintained trainer.py recently"}
            ]
        }
        
        # 3. Call endpoint
        payload = {
            "owner": "huggingface",
            "repo": "transformers",
            "pr_number": 42,
            "required_reviewers": [],
            "options": {"top_k": 5}
        }
        response = client.post("/api/recommend-reviewers", json=payload)
        
        # 4. Assertions
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("recommended_reviewers", json_data)
        self.assertEqual(len(json_data["recommended_reviewers"]), 2)
        self.assertEqual(json_data["recommended_reviewers"][0]["name"], "ArthurZucker")
        self.assertEqual(json_data["recommended_reviewers"][0]["confidence_score"], 90)

    @patch("codience.src.app.analyze_jira_tickets")
    def test_analyze_jira_tickets_endpoint(self, mock_analyze):
        """Test the JIRA tickets analysis API endpoint."""
        mock_analyze.return_value = {"skills": ["Authentication", "FastAPI"], "resolved_count": 5}
        
        payload = {
            "username": "dev_user",
            "tickets": [{"key": "PROJ-101", "summary": "Add OAuth2 integration"}]
        }
        response = client.post("/api/analyze/jira-tickets", json=payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["resolved_count"], 5)


# =====================================================================
# PART 2: RECOMMENDATION SYSTEM EVALUATION (Metrics)
# =====================================================================

def evaluate_recommendations(predictions: list[list[str]], ground_truth: list[list[str]], k_values=[1, 3, 5]):
    """
    Evaluates recommendations using standard IR metrics:
    - Hit Rate@k (HR@k)
    - Mean Reciprocal Rank (MRR)
    - Precision@k
    - Recall@k
    """
    results = {}
    n = len(predictions)
    if n == 0:
        return results

    # 1. Mean Reciprocal Rank (MRR)
    rr_list = []
    for pred, gt in zip(predictions, ground_truth):
        gt_set = set(gt)
        rank = -1
        for i, p in enumerate(pred):
            if p in gt_set:
                rank = i + 1
                break
        rr = 1.0 / rank if rank > 0 else 0.0
        rr_list.append(rr)
    results["MRR"] = float(np.mean(rr_list))

    # 2. Hit Rate, Precision, Recall at different K values
    for k in k_values:
        hits = 0
        precision_list = []
        recall_list = []
        
        for pred, gt in zip(predictions, ground_truth):
            pred_k = pred[:k]
            gt_set = set(gt)
            
            # Intersection of recommended and actual reviewers
            correct_recs = [p for p in pred_k if p in gt_set]
            
            # Hit Rate: at least one correct recommendation
            if len(correct_recs) > 0:
                hits += 1
                
            # Precision@k = correct / recommended
            precision = len(correct_recs) / k
            precision_list.append(precision)
            
            # Recall@k = correct / total actual
            recall = len(correct_recs) / len(gt_set) if len(gt_set) > 0 else 0.0
            recall_list.append(recall)
            
        results[f"HitRate@{k}"] = hits / n
        results[f"Precision@{k}"] = float(np.mean(precision_list))
        results[f"Recall@{k}"] = float(np.mean(recall_list))
        
    return results


def run_model_evaluation_demo():
    """
    Runs a simulation/evaluation matching a ground-truth dataset 
    representing real-world pull requests.
    """
    print("\n" + "="*60)
    # Ground truth: Who actually reviewed these PRs in reality
    ground_truth = [
        ["ArthurZucker"],
        ["younesbelkada", "ArthurZucker"],
        ["younesbelkada"],
        ["ArthurZucker"],
        ["dev_c", "younesbelkada"]
    ]

    # Predictions made by the Recommender (ordered by confidence)
    predictions = [
        ["ArthurZucker", "younesbelkada", "dev_c"],  # PR 1
        ["ArthurZucker", "dev_c", "younesbelkada"],  # PR 2
        ["dev_c", "younesbelkada", "ArthurZucker"],  # PR 3
        ["younesbelkada", "dev_c", "ArthurZucker"],  # PR 4
        ["dev_c", "younesbelkada", "ArthurZucker"]   # PR 5
    ]

    print("📊 Evaluating Recommender System Metrics...")
    metrics = evaluate_recommendations(predictions, ground_truth, k_values=[1, 2, 3])
    
    print("-" * 60)
    for metric, score in metrics.items():
        print(f"🔹 {metric:<15} : {score * 100:.2f}%" if "MRR" not in metric else f"🔹 {metric:<15} : {score:.4f}")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("🧪 Running API Unit Tests...")
    # Run unittest suite programmatically
    suite = unittest.TestLoader().loadTestsFromTestCase(TestReviewerRecommenderAPI)
    unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Run evaluation metrics demonstration
    run_model_evaluation_demo()
