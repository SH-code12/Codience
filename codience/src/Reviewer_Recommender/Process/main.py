from codience.src.Reviewer_Recommender.Process.analysis_PR import extract_pr_skills
from codience.src.Reviewer_Recommender.Data.searching_into_vectordb import search_vector_db
mock_pr_data = {
        "title": "Fix: Optimized SQL Query for User Dashboard",
        "description": "I added an index to the User table and refactored the Entity Framework query to avoid N+1 issues.",
        "diff": """
        --- a/Data/UserRepository.cs
        +++ b/Data/UserRepository.cs
        @@ -10,5 +10,5 @@
        - var users = context.Users.ToList();
        + var users = context.Users.Include(u => u.Posts).AsNoTracking().ToList();
        """
    }


def main():
        # 1. Get the skills from Step 1 (What we just did)
    extraction_result = extract_pr_skills(mock_pr_data)
    skills_to_search = extraction_result['rag_query']

    unified_query = ", ".join(skills_to_search) 

    role_matches = search_vector_db(unified_query, k=5)

    # 3. Final Step: Rank your reviewers based on these roles
# 4. Check the results
    if not role_matches:
        print("⚠️ No direct match found. System might need to fallback to general roles.")
    else:
        for i, match in enumerate(role_matches):
            print(f"Rank {i+1}: {match['metadata']['name']} (Score: {match['score']})")


if __name__ == "__main__":
        main()