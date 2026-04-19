import os
import json
from codience.src.Reviewer_Recommender.Process.Engine_test import ReviewerRecommender
from codience.src.Reviewer_Recommender.Process.scorer_agent import CandidateScore

# Inject some dummy data into history profiles
class MockReviewerRecommender(ReviewerRecommender):
    def initialize_system(self):
        print("🚀 [MOCK] Building Knowledge Base...")
        self.history_profiles = {
            "dev_java": {"Java", "Spring", "SQL"},
            "dev_python": {"Python", "FastAPI", "React"},
            "dev_frontend": {"JavaScript", "React", "CSS"}
        }
        print(f"✅ [MOCK] Indexed {len(self.history_profiles)} developers.")

if __name__ == "__main__":
    print("Starting Mocked System Run to verify AI Agents...")
    
    # Setup the Mock engine
    engine = MockReviewerRecommender("mock_owner", "mock_repo")
    engine.initialize_system()
    
    mock_pr_data = {
        "title": "Add JWT Authentication to API",
        "description": "Implemented JWT token based auth for all backend routes using FastAPI.",
        "diff": "+ import jwt\n+ def verify_token(): pass"
    }

    try:
        # We need to ensure that JIRA_API_BASE_URL is something safe so it fails fast or we mock it
        os.environ["JIRA_API_BASE_URL"] = "http://localhost:9999/api" # will fail fast
        results = engine.recommend(mock_pr_data)
        
        print("\n" + "═"*90)
        print("  ACCURACY-MATCH REPORT (MOCKED)")
        print("═"*90)
        print(f"{'RANK':<5} | {'DEVELOPER':<18} | {'CONF SCORE':<10} | {'JUSTIFICATION'}")
        print("─"*90)

        for i, r in enumerate(results):
            icon = "⭐" if i == 0 else "  "
            conf_score = f"{r.get('confidence_score', 0)}/100"
            justif = r.get('justification', '')[:40] + "..." if len(r.get('justification', '')) > 40 else r.get('justification', '')
            print(f"{icon} #{i+1:<2} | {r['name']:<18} | {conf_score:<10} | {justif}")
        
    except Exception as e:
        print("Exception during mocked run:", e)
