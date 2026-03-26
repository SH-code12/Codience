# Fast API for reviewer recommendation
from fastapi import FastAPI
from pydantic import BaseModel
from codience.src.Reviewer_Recommender.Process.Engine_test import ReviewerRecommender, fetch_real_pr_data
from codience.src.Reviewer_Recommender.Process.analysis_PR import extract_pr_skills
from codience.src.Reviewer_Recommender.Data.searching_into_vectordb import search_vector_db

app = FastAPI()

class ReviewerRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int


@app.post("/api/recommend")
async def recommend(request: ReviewerRequest):
    engine = ReviewerRecommender(request.owner, request.repo)
    engine.initialize_system()

    real_pr = fetch_real_pr_data(request.owner, request.repo, request.pr_number)
    if not real_pr:
        return {"error": "Failed to fetch PR data."}
    
    results = engine.recommend(real_pr)

    formatted_results = []
    for res in results[:5]:
        formatted_results.append({
            "name": res['name'],
            "score": res['score'],
            "skills": res['skills'],
        })
    return {"reviewers": formatted_results}
