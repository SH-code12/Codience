from summarize_pr import summarize_pr

# Mock data shaped like what the .NET backend provides.
mock_pr_data = {
    "title": "Fix: Optimized SQL Query for User Dashboard",
    "description": (
        "I added an index to the User table and refactored the Entity Framework "
        "query to avoid N+1 issues."
    ),
    "diff": """
    --- a/Data/UserRepository.cs
    +++ b/Data/UserRepository.cs
    @@ -10,5 +10,5 @@
    - var users = context.Users.ToList();
    + var users = context.Users.Include(u => u.Posts).AsNoTracking().ToList();
    """,
}


def test_summary():
    print("🚀 Starting Test: Summarizing PR...")
    try:
        summary = summarize_pr(mock_pr_data)
        print("\n--- AI SUMMARY ---")
        print(summary)
        if summary and "unavailable" not in summary.lower():
            print("\n✅ SUCCESS: A summary was generated.")
        else:
            print("\n❌ FAILED: No usable summary was produced.")
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")


if __name__ == "__main__":
    test_summary()
