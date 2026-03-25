# Fast API for reviewer recommendation
from fastapi import FastAPI
from codience.src.Reviewer_Recommender.Process.analysis_PR import extract_pr_skills
from codience.src.Reviewer_Recommender.Data.searching_into_vectordb import search_vector_db

app = FastAPI()

@app.post("/api/recommend")
async def recommend(request: dict):
    extraction_result = extract_pr_skills(request)
    skills_to_search = extraction_result['rag_query']
    
    role_matches = search_vector_db(skills_to_search, k = 20)

    recommendations = []
    for match in role_matches:
        content = match.page_content
        role_title = content.split('|')[0].replace("rag_content: Role:", "").strip()
        recommendations.append(role_title)

    return {
         "reviewers": recommendations,
     }
