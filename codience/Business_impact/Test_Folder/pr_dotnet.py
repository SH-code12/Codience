"""
pr_fetcher_with_dotnet.py - Fetch PRs and enrich with Jira data from .NET backend
Features automatic runtime fallback to native GitHub REST endpoints if the .NET API is offline.
"""

import os
import sys
from typing import List, Optional, Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

from dotnet_jira_client import get_dotnet_client, get_pr_enricher, fetch_authenticated_github_email
from models import PRPayload, JiraTicket

BASE_GITHUB_URL = "https://api.github.com"
DOTNET_BACKEND_BASE_URL = os.getenv("DOTNET_BACKEND_URL", "http://localhost:5051")


class ResilientGitHubClient:
    """
    Smart API client that hits the .NET API controllers by default,
    falling back transparently to native GitHub REST API when needed.
    """

    def __init__(self, github_token: str = None):
        self.token = github_token or os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        
        # Keep an explicit header configuration collection isolated for direct GitHub fallbacks
        self.github_headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        } if self.token else {}

    def is_backend_online(self) -> bool:
        """Heuristic check to establish backend connection readiness."""
        try:
            # Pinging device-code endpoint as a lightweight status health check
            response = self.session.get(f"{DOTNET_BACKEND_BASE_URL}/api/GitHubAuth/device-code", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False

    def get_pull_requests(self, owner: str, repo: str) -> List[Dict]:
        """Fetches PR collection from backend or fallback natively via GitHub."""
        if self.is_backend_online():
            try:
                print("📡 [.NET Backend] Fetching pull request collection...")
                url = f"{DOTNET_BACKEND_BASE_URL}/api/GitHubAuth/{owner}/{repo}/pulls"
                return self.session.get(url, timeout=5.0).json()
            except Exception as e:
                print(f"⚠️ Backend communication dropped during PR list fetch: {e}. Slipping to GitHub REST...")
        
        # Native GitHub API Fallback route
        print("🐙 [Native GitHub] Fetching pull request collection...")
        url = f"{BASE_GITHUB_URL}/repos/{owner}/{repo}/pulls"
        resp = self.session.get(url, headers=self.github_headers, params={"state": "open", "per_page": 30})
        resp.raise_for_status()
        return resp.json()

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """Fetches target modified file matrix collections safely."""
        if self.is_backend_online():
            try:
                url = f"{DOTNET_BACKEND_BASE_URL}/api/GitHubAuth/{owner}/{repo}/pulls/{pr_number}/files"
                return self.session.get(url, timeout=4.0).json()
            except Exception:
                pass

        url = f"{BASE_GITHUB_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        resp = self.session.get(url, headers=self.github_headers, params={"per_page": 50})
        resp.raise_for_status()
        return resp.json()

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetches unified raw context patch data strings directly."""
        # Standard fallback mechanism logic using native Accept media type profiles
        try:
            url = f"{BASE_GITHUB_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
            headers = {**self.github_headers, "Accept": "application/vnd.github.v3.diff"}
            resp = self.session.get(url, headers=headers, timeout=5.0)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return ""

    def get_backend_metrics(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Gathers advanced custom telemetry matrices compiled exclusively by .NET layer."""
        metrics = {"source": "native_fallback"}
        if not self.is_backend_online():
            return metrics

        try:
            metrics["source"] = "dotnet_backend"
            metrics["change"] = self.session.get(f"{DOTNET_BACKEND_BASE_URL}/api/GitHubAuth/{owner}/{repo}/pulls/{pr_number}/metrics").json()
            metrics["history"] = self.session.get(f"{DOTNET_BACKEND_BASE_URL}/api/GitHubAuth/{owner}/{repo}/pulls/{pr_number}/history").json()
            metrics["experience"] = self.session.get(f"{DOTNET_BACKEND_BASE_URL}/api/GitHubAuth/{owner}/{repo}/pulls/{pr_number}/experience").json()
            metrics["commits_analytics"] = self.session.get(f"{DOTNET_BACKEND_BASE_URL}/api/PRCommits/repos/{owner}/{repo}/pullrequests/{pr_number}/commits/metrics").json()
        except Exception as e:
            print(f"⚠️ Structural telemetry pipeline pull skipped: {e}")
        return metrics


class PRFetcherWithDotNet:
    """Resilient fetcher coordinating data gathering and Jira pipeline enrichment."""

    def __init__(self, github_token: str = None):
        self.github = ResilientGitHubClient(github_token)
        self.dotnet_client = get_dotnet_client()
        self.pr_enricher = get_pr_enricher()

    def fetch_open_prs(self, repo_name: str, max_prs: int = 20, user_email: str = "") -> List[PRPayload]:
        owner, repo = self._split_repo(repo_name)
        if not owner:
            return []

        pr_payloads: List[PRPayload] = []

        try:
            batch = self.github.get_pull_requests(owner, repo)
            if not batch:
                return []

            for pr_data in batch[:max_prs]:
                # Dynamic normalization to accommodate different naming styles (e.g., camelCase vs snake_case)
                pr_num = pr_data.get("number") or pr_data.get("prNumber") or pr_data.get("id")
                pr_title = pr_data.get("title") or pr_data.get("prTitle")
                
                print(f"📥 Processing PR #{pr_num}: {pr_title}")

                payload = self._github_pr_to_dict(pr_data, owner, repo, pr_num, pr_title)
                
                # Apply live runtime context data parsing layers
                enriched_payload = self.pr_enricher.enrich_pr_with_jira(payload, fallback_email=user_email)
                
                pr_payload = self._dict_to_pr_payload(enriched_payload, owner, repo, pr_num)
                pr_payloads.append(pr_payload)

            print(f"\n✅ Successfully structured {len(pr_payloads)} PR records.")

        except Exception as e:
            print(f"❌ Critical failure during compilation loops: {e}")

        return pr_payloads

    @staticmethod
    def _split_repo(repo_name: str):
        parts = repo_name.split("/", 1)
        if len(parts) != 2 or not all(parts):
            print(f"❌ Invalid repo format '{repo_name}'. Expected 'owner/repo'.")
            return None, None
        return parts[0], parts[1]

    def _github_pr_to_dict(self, pr: Dict[str, Any], owner: str, repo: str, pr_num: int, pr_title: str) -> Dict[str, Any]:
        user_node = pr.get("user") or {}
        author = pr.get("author") or user_node.get("login") or "unknown"
        
        milestone = pr.get("milestone") or {}
        due_on = pr.get("milestoneDueDate") or milestone.get("due_on")

        labels = pr.get("githubLabels") or [lbl.get("name") for lbl in pr.get("labels", [])]

        return {
            "pr_number": pr_num,
            "pr_title": pr_title,
            "pr_body": pr.get("body") or pr.get("prBody") or "",
            "repo_owner": owner,
            "repo_name": repo,
            "head_branch": pr.get("headBranch") or (pr.get("head") or {}).get("ref") or "main",
            "base_branch": pr.get("baseBranch") or (pr.get("base") or {}).get("ref") or "main",
            "author": author,
            "github_labels": labels,
            "milestone_due_date": due_on,
        }

    def _dict_to_pr_payload(self, data: Dict[str, Any], owner: str, repo: str, pr_number: int) -> PRPayload:
        jira_tickets: List[JiraTicket] = []
        for t in data.get("linked_jira_tickets", []):
            jira_tickets.append(
                JiraTicket(
                    key=t.get("key", ""),
                    summary=t.get("summary", ""),
                    severity=t.get("severity", "medium"),
                    priority=t.get("priority", "medium"),
                    labels=t.get("labels", []),
                    affected_users_count=t.get("affected_users_count"),
                    description=t.get("description", ""),
                    status=t.get("status", "Unknown"),
                )
            )

        # Pull system file arrays
        files = self.github.get_pr_files(owner, repo, pr_number)
        changed_files = [f.get("filename") or f.get("fileName") for f in files[:50] if f]

        # RECONSTRUCT OR EXTRACT CODES PATCH DIFF STRING
        diff_excerpt = self.github.get_pr_diff(owner, repo, pr_number)
        
        if not diff_excerpt:
            # Reconstruct string by parsing internal line chunks manually
            diff_parts = []
            for f in files[:30]:
                fname = f.get("filename") or f.get("fileName")
                patch = f.get("patch") or f.get("Patch") or ""
                if fname and patch:
                    diff_parts.append(f"diff --git a/{fname} b/{fname}\n{patch}")
            diff_excerpt = "\n".join(diff_parts)

        # Inject telemetry block into payload metadata variables for reference downstream
        backend_metrics = self.github.get_backend_calculated_metrics(owner, repo, pr_number) if hasattr(self.github, 'get_backend_calculated_metrics') else self.github.get_backend_metrics(owner, repo, pr_number)
        
        return PRPayload(
            pr_number=data["pr_number"],
            pr_title=data["pr_title"],
            pr_body=data["pr_body"],
            repo_owner=data["repo_owner"],
            repo_name=data["repo_name"],
            head_branch=data["head_branch"],
            base_branch=data["base_branch"],
            diff_excerpt=diff_excerpt[:6000],
            changed_files=changed_files,
            github_labels=data["github_labels"],
            milestone_due_date=data.get("milestone_due_date"),
            linked_jira_tickets=jira_tickets,
        )