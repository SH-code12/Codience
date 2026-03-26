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
        # Increased to 100 to find more developers
        print(f"🚀 Building Knowledge Base from last 100 commits...")
        commits = fetch_commits(self.owner, self.repo, per_page=100)
        self.history_profiles = map_commits_to_skills(commits)
        print(f"✅ Indexed {len(self.history_profiles)} developers.")

    def recommend(self, pr_data):
        analysis = extract_pr_skills(pr_data)
        # The LLM returns full names like "Python", "JavaScript"
        # Ensure they are formatted to match your helper's mapping (Title Case)
        required_languages = {lang.strip().title() for lang in analysis.get('detected_languages', [])}
        
        # Fix for C# specifically if needed
        if "C#" in required_languages:
            required_languages.remove("C#")
            required_languages.add(".NET")

        rankings = []
        for name, dev_skills in self.history_profiles.items():
            # dev_skills now contains {"Python", "Java"} etc. from the helper
            matched_skills = required_languages.intersection(dev_skills)
            
            score = len(matched_skills) / len(required_languages) if required_languages else 0
            
            rankings.append({
                "name": name,
                "score": round(score, 2),
                "skills": list(matched_skills), 
                "analysis_summary": analysis.get('rag_query', '')
            })

        return sorted(rankings, key=lambda x: x['score'], reverse=True)

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
        print(f"{'RANK':<5} | {'DEVELOPER':<18} | {'MATCH %':<8} | {'MATCHED SKILLS'}")
        print("─"*90)

        for i, r in enumerate(results):
            icon = "⭐" if i == 0 else "  "
            skills_str = ", ".join(r['skills']) if r['skills'] else "---"
            match_pct = f"{r['score'] * 100:>5.0f}%"
            
            print(f"{icon} #{i+1:<2} | {r['name']:<18} | {match_pct} | {skills_str}")
        
        print("═"*90)
        if results and results[0]['score'] > 0:
            print(f"🏆 BEST MATCH: {results[0]['name']}")
            print(f"   Matches: {', '.join(results[0]['skills'])}")
        else:
            print("⚠️ No strong matches found in recent history.")
        print("═"*90)