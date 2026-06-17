import asyncio
import json
import os
import requests as _requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from pr_fetcher_with_dotnet import PRFetcherWithDotNet
from dotnet_jira_client import get_dotnet_client, fetch_authenticated_github_email
from coreRanking import PRRankingEngine
from models import ImpactTier


def check_dotnet_connection(client) -> bool:
    """
    Verify the .NET backend is reachable WITHOUT calling /me.
    A GET to the login URL is enough — no token required.
    """
    try:
        resp = _requests.get(
            client.get_login_url(),
            timeout=client.timeout,
            allow_redirects=False,
        )
        print(f"✅ .NET backend is reachable (HTTP {resp.status_code})")
        return True
    except _requests.ConnectionError:
        print("❌ Cannot reach .NET backend — is it running on port 5051?")
        return False
    except Exception as e:
        print(f"❌ Unexpected error checking backend: {e}")
        return False


async def main():
    print("=" * 80)
    print("🚀 PR BUSINESS IMPACT RANKING - WITH .NET BACKEND")
    print("=" * 80)

    print("\n📋 Configuration:")
    print(f"   .NET API URL:  {os.getenv('DOTNET_API_URL', 'http://localhost:5051/api')}")
    print(f"   GitHub Token:  {'✅' if os.getenv('GITHUB_TOKEN') else '❌'}")
    print(f"   GitHub Repo:   {os.getenv('GITHUB_REPO', 'Not set')}")
    print(f"   Jira Token:    {'✅' if os.getenv('JIRA_API_TOKEN') else '❌'}")

    # ── connectivity check (no /me, no token needed) ──────────────────
    print("\n🔌 Testing .NET Backend Connection...")
    client = get_dotnet_client()

    if not check_dotnet_connection(client):
        print("   Start the backend with: dotnet run")
        return

    if client.access_token:
        print("✅ Jira token loaded — enrichment enabled.")
    else:
        print("⚠️  No Jira token. Jira enrichment will be skipped.")
        print(f"   Authenticate at: {client.get_login_url()}")

    # ── fetch user email identity dynamically via github API ─────────
    print("\n🔐 Fetching authenticated user profile context from GitHub...")
    user_email = fetch_authenticated_github_email()
    if user_email:
        print(f"   ✓ Extracted active identity mapping email: {user_email}")
    else:
        print("   ⚠️ User identity extraction failed. Proceeding with fallback metrics.")
        user_email = "unknown@domain.internal"

    # ── fetch PRs ─────────────────────────────────────────────────────
    print("\n📥 Fetching PRs from GitHub and enriching with Jira...")
    fetcher = PRFetcherWithDotNet()

    repo_name = os.getenv("GITHUB_REPO")
    if not repo_name or repo_name == "your-org/your-repo":
        print("\n📝 Enter GitHub repository (format: owner/repo):")
        repo_name = input("> ").strip()
        if not repo_name:
            print("No repository provided. Exiting.")
            return

    prs = fetcher.fetch_open_prs(repo_name, max_prs=10, user_email=user_email)
    if not prs:
        print("\n❌ No PRs found or unable to fetch.")
        return

    # ── rank PRs ──────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("🎯 RANKING PRS WITH BUSINESS IMPACT")
    print(f"{'=' * 60}")

    engine = PRRankingEngine()
    scored_results = []
    for pr in prs:
        # Pass the verified email string context directly into the scoring pipeline
        result = await engine.score_single_pr(pr, reporter_email=user_email)
        scored_results.append(result)

    ranked = sorted(scored_results, key=lambda r: r.weighted_score, reverse=True)

    # ── display ───────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("📊 RANKED RESULTS")
    print(f"{'=' * 60}")

    tier_icons = {ImpactTier.HIGH: "🔴", ImpactTier.MEDIUM: "🟡", ImpactTier.LOW: "🟢"}

    for i, r in enumerate(ranked, 1):
        icon = tier_icons.get(r.tier, "⚪")
        print(f"\n{i}. {icon} PR #{r.pr_number}: {r.pr_title[:60]}")
        print(f"   Score: {r.weighted_score:.1f}/100  |  Tier: {r.tier.value.upper()}")
        print(f"   Block merge: {'⚠️  YES' if r.should_block_merge else 'NO'}")
        bd = r.score_breakdown or {}
        print(f"   Business Impact: {bd.get('business_impact', 0):.2f}  |  "
              f"User Exposure: {bd.get('user_exposure', 0):.2f}")

    # ── save ──────────────────────────────────────────────────────────
    output_file = Path(__file__).parent / "dotnet_results.json"
    results_data = [
        {
            "pr_number":          r.pr_number,
            "pr_title":           r.pr_title,
            "weighted_score":     r.weighted_score,
            "tier":               r.tier.value,
            "should_block_merge": r.should_block_merge,
            "score_breakdown":    r.score_breakdown or {},
        }
        for r in ranked
    ]
    with open(output_file, "w") as f:
        json.dump(results_data, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

    # ── Jira summary ──────────────────────────────────────────────────
    print("\n📋 Jira Tickets Summary:")
    all_tickets: dict = {}
    for pr in prs:
        for ticket in pr.linked_jira_tickets:
            if ticket.key not in all_tickets:
                all_tickets[ticket.key] = {
                    "summary":  ticket.summary,
                    "severity": ticket.severity,
                    "priority": ticket.priority,
                }
    if all_tickets:
        for key, info in list(all_tickets.items())[:10]:
            print(f"   {key}: {info['summary'][:50]}  (Severity: {info['severity']})")
    else:
        print("   No Jira tickets linked to any of the fetched PRs.")


if __name__ == "__main__":
    asyncio.run(main())