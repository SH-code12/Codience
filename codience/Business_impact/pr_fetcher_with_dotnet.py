"""
pr_fetcher_with_dotnet.py - Fetch PRs and enrich with Jira data from .NET backend
Uses GitHub REST API directly (no PyGithub dependency).
"""

import os
import sys
from typing import List, Optional, Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

from dotnet_jira_client import get_dotnet_client, get_pr_enricher, fetch_authenticated_github_email
from models import PRPayload, JiraTicket

BASE_URL = "https://api.github.com"


class GitHubAPIClient:
    """
    Thin wrapper around the GitHub REST API using requests.
    Replaces the PyGithub dependency.
    """

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        })

    def _get(self, path: str, params: Dict = None) -> Any:
        url = f"{BASE_URL}{path}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
        page: int = 1,
    ) -> List[Dict]:
        return self._get(
            f"/repos/{owner}/{repo}/pulls",
            params={
                "state": state,
                "sort": sort,
                "direction": direction,
                "per_page": per_page,
                "page": page,
            },
        )

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Dict:
        return self._get(f"/repos/{owner}/{repo}/pulls/{pr_number}")

    def get_pr_files(self, owner: str, repo: str, pr_number: int, per_page: int = 50) -> List[Dict]:
        return self._get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
            params={"per_page": per_page},
        )

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        response = self.session.get(url, headers={"Accept": "application/vnd.github.v3.diff"})
        if response.status_code == 200:
            return response.text
        return ""


class PRFetcherWithDotNet:
    """
    Fetch PRs from GitHub and enrich with Jira data from your .NET backend.
    Uses the GitHub REST API directly — no PyGithub required.
    """

    def __init__(self, github_token: str = None):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github: Optional[GitHubAPIClient] = (
            GitHubAPIClient(self.github_token) if self.github_token else None
        )
        self.dotnet_client = get_dotnet_client()
        self.pr_enricher = get_pr_enricher()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def fetch_open_prs(self, repo_name: str, max_prs: int = 20, user_email: str = "") -> List[PRPayload]:
        """
        Fetch open PRs from GitHub and enrich with Jira data using runtime email overrides.
        """
        if not self.github:
            print("❌ GitHub client not initialized. Set GITHUB_TOKEN")
            return []

        owner, repo = self._split_repo(repo_name)
        if not owner:
            return []

        pr_payloads: List[PRPayload] = []

        try:
            fetched = 0
            page = 1
            while fetched < max_prs:
                batch = self.github.get_pull_requests(
                    owner, repo,
                    state="open",
                    sort="created",
                    direction="desc",
                    per_page=min(30, max_prs - fetched),
                    page=page,
                )
                if not batch:
                    break

                for pr_data in batch:
                    if fetched >= max_prs:
                        break

                    print(f"\n📥 Processing PR #{pr_data['number']}: {pr_data['title']}")

                    payload = self._github_pr_to_dict(pr_data, owner, repo)
                    
                    # Forwarding live identities cleanly down to the enricher pipeline wrapper
                    enriched_payload = self.pr_enricher.enrich_pr_with_jira(payload, fallback_email=user_email)
                    
                    pr_payload = self._dict_to_pr_payload(enriched_payload, pr_data, owner, repo)
                    pr_payloads.append(pr_payload)
                    fetched += 1

                page += 1

            print(f"\n✅ Processed {len(pr_payloads)} PRs")

        except requests.HTTPError as e:
            print(f"❌ GitHub API error: {e}")
        except Exception as e:
            print(f"❌ Error fetching PRs: {e}")

        return pr_payloads

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_repo(repo_name: str):
        """Split 'owner/repo' into (owner, repo). Returns (None, None) on error."""
        parts = repo_name.split("/", 1)
        if len(parts) != 2 or not all(parts):
            print(f"❌ Invalid repo format '{repo_name}'. Expected 'owner/repo'.")
            return None, None
        return parts[0], parts[1]

    def _github_pr_to_dict(
        self, pr: Dict[str, Any], owner: str, repo: str
    ) -> Dict[str, Any]:
        """Convert a GitHub REST API PR object to the dict format used for enrichment."""
        milestone = pr.get("milestone") or {}
        due_on = milestone.get("due_on")

        return {
            "pr_number": pr["number"],
            "pr_title": pr["title"],
            "pr_body": pr.get("body") or "",
            "repo_owner": owner,
            "repo_name": repo,
            "head_branch": pr["head"]["ref"],
            "base_branch": pr["base"]["ref"],
            "author": pr["user"]["login"],
            "github_labels": [lbl["name"] for lbl in pr.get("labels", [])],
            "milestone_due_date": due_on,
        }

    def _dict_to_pr_payload(
        self,
        data: Dict[str, Any],
        pr: Dict[str, Any],
        owner: str,
        repo: str,
    ) -> PRPayload:
        """Convert enriched dict + raw PR data into a PRPayload model."""
        jira_tickets: List[JiraTicket] = []
        for ticket_data in data.get("linked_jira_tickets", []):
            jira_tickets.append(
                JiraTicket(
                    key=ticket_data.get("key", ""),
                    summary=ticket_data.get("summary", ""),
                    severity=ticket_data.get("severity", "medium"),
                    priority=ticket_data.get("priority", "medium"),
                    labels=ticket_data.get("labels", []),
                    affected_users_count=ticket_data.get("affected_users_count"),
                    description=ticket_data.get("description", ""),
                    status=ticket_data.get("status", "Unknown"),
                )
            )

        diff = self._get_pr_diff(owner, repo, pr["number"])

        files = self.github.get_pr_files(owner, repo, pr["number"], per_page=50)
        changed_files = [f["filename"] for f in files[:50]]

        return PRPayload(
            pr_number=data["pr_number"],
            pr_title=data["pr_title"],
            pr_body=data["pr_body"],
            repo_owner=data["repo_owner"],
            repo_name=data["repo_name"],
            head_branch=data["head_branch"],
            base_branch=data["base_branch"],
            diff_excerpt=diff[:6000],
            changed_files=changed_files,
            github_labels=data["github_labels"],
            milestone_due_date=data.get("milestone_due_date"),
            linked_jira_tickets=jira_tickets,
        )

    def _get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetch the unified diff for a PR."""
        try:
            diff = self.github.get_pr_diff(owner, repo, pr_number)
            if diff:
                return diff
        except Exception as e:
            print(f"⚠️ Could not fetch diff via Accept header: {e}")

        try:
            files = self.github.get_pr_files(owner, repo, pr_number, per_page=20)
            diff_parts: List[str] = []
            for f in files[:20]:
                diff_parts.append(f"diff --git a/{f['filename']} b/{f['filename']}")
                if f.get("patch"):
                    diff_parts.append(f["patch"][:1000])
            return "\n".join(diff_parts)
        except Exception as e:
            print(f"⚠️ Could not build fallback diff: {e}")
            return ""


# ---------------------------------------------------------------------------
# Smoke-test / manual integration test
# ---------------------------------------------------------------------------

async def test_with_dotnet_backend():
    """
    Quick integration test for the .NET backend + GitHub API.
    """
    print("=" * 80)
    print("🧪 TESTING .NET BACKEND INTEGRATION")
    print("=" * 80)

    # 1. Test .NET API connection
    print("\n📡 Testing .NET API connection...")
    client = get_dotnet_client()

    try:
        if client.access_token:
            user = client.get_current_user()
            print(f"✅ Connected to .NET API as: {user.get('displayName', 'Unknown')}")
        else:
            print("⚠️ No access token. Please authenticate via OAuth first.")
            print(f"   Login URL: {client.get_login_url()}")
    except Exception as e:
        print(f"⚠️ Could not connect to .NET API: {e}")
        print("   Make sure your .NET backend is running on http://localhost:5051")

    # 2. Extract identity string safely context via direct endpoints
    print("\n🔐 Resolving direct active profile contexts...")
    user_email = fetch_authenticated_github_email()
    if user_email:
        print(f"   ✓ Extracted runtime fallback identifier: {user_email}")
    else:
        print("   ⚠️ Direct profile extraction failed. Using environment attributes.")
        user_email = ""

    # 3. Test fetching Jira tickets
    print("\n📋 Testing ticket fetch...")
    try:
        # Prioritize live extracted email context over hardcoded placeholder names
        test_user = user_email or os.getenv("TEST_JIRA_USER", "shahd")
        tickets = client.get_assigned_tickets(assignee_name=test_user)
        print(f"✅ Found {len(tickets)} tickets for {test_user}")
        if tickets:
            print(f"   Sample: {tickets[0].get('key')} - {tickets[0].get('summary', '')[:50]}")
    except Exception as e:
        print(f"⚠️ Error fetching tickets: {e}")

    # 4. Test PR enrichment
    print("\n🔍 Testing PR enrichment...")
    fetcher = PRFetcherWithDotNet()

    repo_name = os.getenv("GITHUB_REPO")
    if repo_name and repo_name != "your-org/your-repo":
        # ✅ Fixed test scenario to route identity context into the local engine
        prs = fetcher.fetch_open_prs(repo_name, max_prs=5, user_email=user_email)
        print(f"\n✅ Processed {len(prs)} PRs with Jira enrichment")

        for pr in prs:
            print(f"\n   PR #{pr.pr_number}: {pr.pr_title[:50]}")
            if pr.linked_jira_tickets:
                print(f"     Jira: {', '.join(t.key for t in pr.linked_jira_tickets)}")
    else:
        print("⚠️ Set GITHUB_REPO in .env to test PR fetching")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_with_dotnet_backend())