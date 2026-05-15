from codience.src.Reviewer_Recommender.Process.analysis_PR import extract_pr_skills
from codience.src.Reviewer_Recommender.Data.searching_into_vectordb import search_vector_db
from codience.src.Reviewer_Recommender.Process.tests_prs import test_prs


def main():
    for mock_pr_data in test_prs:
        print(f"\nProcessing PR: {mock_pr_data['title']}")
        extraction_result = extract_pr_skills(mock_pr_data)
        print(f"Extracted Skills: {extraction_result['required_skills']}")
        print(f"RAG Query: {extraction_result['rag_query']}")
        skills_to_search = extraction_result['rag_query']


        role_matches = search_vector_db(skills_to_search, k=20)

        # 3. Final Step: Rank your reviewers based on these roles
    # 4. Check the results
        if not role_matches:
            print("⚠️ No direct match found. System might need to fallback to general roles.")
        else:
            for i, match in enumerate(role_matches):
                # Extract the role title from the page_content string
                content = match.page_content
                role_title = content.split('|')[0].replace("rag_content: Role:", "").strip()
                
                print(f"Rank {i+1}: {role_title}")
                    # Show more details for verification
                print(f"   Matches: {content.split('|')[1][:100]}...")

if __name__ == "__main__":
        main()