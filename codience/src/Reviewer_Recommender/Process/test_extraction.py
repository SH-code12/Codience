import json
from analysis_PR import extract_pr_skills

def test_ai_extraction():
    # 1. Prepare fake data that looks like it came from .NET
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

    print("🚀 Starting Test: Extracting Skills...")

    try:
        # 2. Run your extraction logic
        result = extract_pr_skills(mock_pr_data)

        # 3. Print the results nicely
        print("\n--- AI OUTPUT ---")
        print(f"Summary: {result.get('summary')}")
        print(f"Skills Extracted: {result.get('required_skills')}")

        # 4. Basic Assertions (Validation)
        if "required_skills" in result and len(result["required_skills"]) > 0:
            print("\n✅ SUCCESS: Skills were identified.")
        else:
            print("\n❌ FAILED: No skills were found.")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_ai_extraction()