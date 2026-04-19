import os
import time
import json
import requests
from google import genai
from google.genai import errors
from dotenv import load_dotenv
from codience.src.Reviewer_Recommender.Process.analysis_PR import extract_pr_skills

# Import your history logic
from codience.src.Reviewer_Recommender.Process.Reviewer_Engine_Helper import fetch_commits, map_commits_to_skills
from codience.src.Reviewer_Recommender.Process.prompts import SKILL_EXTRACTION_PROMPT

# Import AI Agents
from codience.src.Reviewer_Recommender.Process.jira_agent import analyze_jira_context
from codience.src.Reviewer_Recommender.Process.scorer_agent import calculate_match_scores
from codience.src.Reviewer_Recommender.Data.searching_into_vectordb import search_vector_db

load_dotenv()

# --- 1. FETCH REAL DATA ---
def fetch_real_pr_data(owner, repo, pr_number):
    print(f"📡 Fetching Real PR #{pr_number} from {owner}/{repo}...")
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3.diff" 
    }
    
    pr_resp = requests.get(pr_url, headers={"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"})
    if pr_resp.status_code != 200:
        print(f"❌ Failed to fetch PR info: {pr_resp.status_code}")
        return None
        
    pr_json = pr_resp.json()
    diff_resp = requests.get(pr_url, headers=headers)
    
    return {
        "title": pr_json.get("title"),
        "description": pr_json.get("body") or "No description provided.",
        "diff": diff_resp.text[:3000] 
    }

# --- 2. AI SKILL EXTRACTION ---
# -----------function already implemented in analysis_PR.py for better modularity and testing-----------
# def extract_pr_skills(pr_data):
#     client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
#     # FIX: Using the direct model name string to avoid 404
#     model_name = "gemini-3.1-flash-lite-preview" 

#     prompt = SKILL_EXTRACTION_PROMPT.format(
#         title=pr_data['title'],
#         description=pr_data['description'],
#         diff=pr_data['diff']
#     )

#     try:
#         time.sleep(1) # Small delay
#         response = client.models.generate_content(model=model_name, contents=prompt)
#         text = response.text.strip()
        
#         # Robust JSON cleaning
#         if "```json" in text:
#             text = text.split("```json")[1].split("```")[0].strip()
#         elif "```" in text:
#             text = text.split("```")[1].strip()
            
#         return json.loads(text)
#     except Exception as e:
#         # FIX: Dynamic fallback based on the actual repository language
#         main_lang = pr_data.get('repo_lang', 'Python')
#         print(f"⚠️ AI Error: {e}. Falling back to {main_lang}.")
#         return {"required_skills": [main_lang], "rag_query": f"{main_lang} expert"}

# --- 3. THE UPDATED ENGINE ---
class ReviewerRecommender:
    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo
        self.history_profiles = {}

    def initialize_system(self):
        # Reduced to 5 for fast testing without RemoteConnectionClosed errors
        print(f"🚀 Building Knowledge Base from last 5 commits...")
        commits = fetch_commits(self.owner, self.repo, per_page=5)
        self.history_profiles = map_commits_to_skills(commits)
        print(f"✅ Indexed {len(self.history_profiles)} developers.")

    def recommend(self, pr_data):
        # 1. PR Analyzer Agent
        analysis = extract_pr_skills(pr_data)
        required_languages = {lang.strip().title() for lang in analysis.get('detected_languages', [])}
        
        if "C#" in required_languages:
            required_languages.remove("C#")
            required_languages.add(".NET")

        # 2. Vector DB RAG Search
        rag_query = analysis.get('rag_query', '') or ', '.join(required_languages)
        try:
            rag_roles = search_vector_db(rag_query, k=10) if rag_query else []
        except Exception as e:
            print(f"⚠️ Vector DB Search Failed: {e}")
            rag_roles = []

        # 3. Preliminary Candidate Filtering (to save API / LLM time)
        # We find up to 10 candidates whose commit history matches at least one requirement
        preliminary_candidates = []
        for name, dev_skills in self.history_profiles.items():
            matched_skills = required_languages.intersection(dev_skills)
            score = len(matched_skills) / max(len(required_languages), 1)
            preliminary_candidates.append({
                "name": name,
                "commit_skills": list(dev_skills),
                "matched_skills": list(matched_skills),
                "prelim_score": score
            })
            
        preliminary_candidates = sorted(preliminary_candidates, key=lambda x: x['prelim_score'], reverse=True)[:10]

        # 4. Jira Analyzer Agent (Enrich candidates)
        for c in preliminary_candidates:
            print(f"🔄 Analyzing Jira Context for {c['name']}...")
            c["jira_context"] = analyze_jira_context(c["name"])

        # 5. Scorer Matchmaker Agent
        print("🧠 Calculating AI Confidence Scores...")
        rankings = calculate_match_scores(analysis, rag_roles, preliminary_candidates)

        return rankings

if __name__ == "__main__":
    # Test on a repo that uses your skills (Java/SQL/Web)
    # https://api.github.com/repos/huggingface/transformers # 44935
    # https://api.github.com/repos/spring-petclinic/spring-framework-petclinic # 249
    TARGET_OWNER = "huggingface"
    TARGET_REPO = "transformers"
    PR_NUMBER = 44935 # Example PR number

    engine = ReviewerRecommender(TARGET_OWNER, TARGET_REPO)
    engine.initialize_system()

    real_pr = fetch_real_pr_data(TARGET_OWNER, TARGET_REPO, PR_NUMBER)

    if real_pr:
        results = engine.recommend(real_pr)
        
        print("\n" + "═"*90)
        print(f"  ACCURACY-MATCH REPORT: {TARGET_REPO}")
        print("═"*90)
        print(f"{'RANK':<5} | {'DEVELOPER':<18} | {'CONF SCORE':<10} | {'JUSTIFICATION'}")
        print("─"*90)

        for i, r in enumerate(results):
            icon = "⭐" if i == 0 else "  "
            conf_score = f"{r.get('confidence_score', 0)}/100"
            justif = r.get('justification', '')[:40] + "..." if len(r.get('justification', '')) > 40 else r.get('justification', '')
            
            print(f"{icon} #{i+1:<2} | {r['name']:<18} | {conf_score:<10} | {justif}")
        
        print("═"*90)
        if results and results[0].get('confidence_score', 0) > 0:
            print(f"🏆 BEST MATCH: {results[0]['name']}")
            print(f"   Reason: {results[0].get('justification', 'N/A')}")
        else:
            print("⚠️ No strong matches found in recent history.")
        print("═"*90)