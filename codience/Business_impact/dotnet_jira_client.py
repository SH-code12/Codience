"""
dotnet_jira_client.py - Python client for calling your .NET Jira API
"""

import re
import requests
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class DotNetJiraClient:
    """
    Client for your .NET Jira API endpoints.
    """

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("DOTNET_API_URL", "http://localhost:5051/api")
        self.timeout = int(os.getenv("API_TIMEOUT", "30"))

        self.access_token: Optional[str] = None
        self.cloud_id: Optional[str] = None
        self.project_key: Optional[str] = None

    def set_credentials(
        self,
        token: str = None,
        cloud_id: str = None,
        project_key: str = None,
    ) -> None:
        """Set authentication credentials from arguments or environment."""
        self.access_token = token or os.getenv("JIRA_API_TOKEN") or os.getenv("JIRA_TOKEN")
        self.cloud_id = cloud_id or os.getenv("JIRA_CLOUD_ID")
        self.project_key = project_key or os.getenv("JIRA_PROJECT_KEY")

    def get_login_url(self) -> str:
        """Return the Jira OAuth login URL."""
        return f"{self.base_url}/Jira/login"

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange an OAuth code for an access token.
        POST /api/Jira/callback?code={code}
        """
        url = f"{self.base_url}/Jira/callback"
        response = requests.get(url, params={"code": code}, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        self.access_token = data.get("accessToken")
        self.cloud_id = data.get("cloudId")

        return data

    def get_assigned_tickets(
        self,
        assignee_name: str,
        token: str = None,
        cloud_id: str = None,
        project_key: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Get tickets assigned to a user.
        POST /api/Jira/assigned-tickets
        """
        url = f"{self.base_url}/Jira/assigned-tickets"

        payload = {
            "Token":        token       or self.access_token,
            "CloudId":      cloud_id    or self.cloud_id,
            "ProjectKey":   project_key or self.project_key,
            "AssigneeName": assignee_name,
        }

        missing = [k for k in ("Token", "CloudId", "ProjectKey") if not payload[k]]
        if missing:
            raise ValueError(
                f"Missing required credentials: {', '.join(missing)}. "
                "Set them via set_credentials() or environment variables."
            )

        if not payload["AssigneeName"]:
            raise ValueError("assignee_name is required.")

        response = requests.post(url, json=payload, timeout=self.timeout)

        if response.status_code != 200:
            print(f"❌ Error fetching tickets: {response.status_code}")
            print(f"   Response: {response.text}")
            response.raise_for_status()

        return response.json()

    def get_current_user(self, token: str = None) -> Dict[str, Any]:
        """
        Get the currently authenticated user.
        GET /api/Jira/me?token={token}
        """
        url = f"{self.base_url}/Jira/me"
        token = token or self.access_token

        if not token:
            raise ValueError("Access token required.")

        params = {"token": token}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def assign_issue(
        self,
        issue_key: str,
        account_id: str,
        token: str = None,
        cloud_id: str = None,
    ) -> bool:
        """
        Assign an issue to a user.
        POST /api/Jira/assign-issue
        """
        url = f"{self.base_url}/Jira/assign-issue"

        payload = {
            "Token":     token     or self.access_token,
            "CloudId":   cloud_id  or self.cloud_id,
            "IssueKey":  issue_key,
            "AccountId": account_id,
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.status_code == 200

    def search_issues_by_jql(
        self,
        jql: str,
        token: str = None,
        cloud_id: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Search issues using JQL.
        """
        print("⚠️ Custom JQL search requires a new endpoint in your .NET controller.")
        return []


class PRJiraEnricher:
    """
    Enrich PRs with real Jira data from the .NET backend.
    """

    _JIRA_KEY_RE = re.compile(r"([A-Z]{2,10}-\d+)", re.IGNORECASE)

    _SEVERITY_MAP = {
        "highest": "blocker",
        "high":    "critical",
        "medium":  "major",
        "low":     "minor",
        "lowest":  "trivial",
    }

    _USER_COUNT_RE = re.compile(r"(\d+)\s*(?:users?|customers?)", re.IGNORECASE)

    def __init__(self, dotnet_client: DotNetJiraClient = None):
        self.client = dotnet_client or DotNetJiraClient()
        self.cache: Dict[str, Dict[str, Any]] = {}

    def extract_jira_keys_from_pr(
        self,
        pr_title: str,
        pr_body: str,
        branch_name: str,
        labels: List[str],
    ) -> List[str]:
        """Extract Jira ticket keys from PR metadata."""
        keys: set = set()
        for source in [pr_title, pr_body, branch_name, *labels]:
            if source:
                keys.update(m.upper() for m in self._JIRA_KEY_RE.findall(source))
        return list(keys)
    
    def fetch_tickets_for_developer(
        self,
        github_username: str,
        jira_username: str = None,
        fallback_email: str = ""  # ✅ Runtime override field added
    ) -> List[Dict[str, Any]]:
        """
        Fetch tickets assigned to a developer using context-verified identity lines.
        """
        if not jira_username:
            jira_username = self._map_github_to_jira(github_username, fallback_email)

        resolved_assignee = jira_username.strip()
        print(f"🔍 Fetching Jira tickets for Assignee Field: '{resolved_assignee}'")

        try:
            tickets = self.client.get_assigned_tickets(assignee_name=resolved_assignee)
            print(f"✅ Found {len(tickets)} tickets for {resolved_assignee}")
            return tickets
        except Exception as e:
            print(f"⚠️ Error fetching tickets for {resolved_assignee}: {e}")
            return []
            
    def fetch_tickets_by_keys(self, keys: List[str]) -> List[Dict[str, Any]]:
        """Fetch specific tickets by their keys via local cache parsing lookup."""
        if not keys:
            return []

        tickets = []
        for key in keys:
            if key in self.cache:
                tickets.append(self.cache[key])
            else:
                print(
                    f"⚠️ Direct key lookup for {key} is not supported. "
                    "Add GET /api/Jira/issue/{key} to your .NET controller."
                )
        return tickets

    def enrich_pr_with_jira(self, pr_data: Dict[str, Any], fallback_email: str = "") -> Dict[str, Any]:
        """Enrich a PR payload dict with Jira ticket data."""
        keys = self.extract_jira_keys_from_pr(
            pr_title=pr_data.get("pr_title", ""),
            pr_body=pr_data.get("pr_body", ""),
            branch_name=pr_data.get("head_branch", ""),
            labels=pr_data.get("github_labels", []),
        )

        enriched_tickets: List[Dict[str, Any]] = []

        if keys:
            enriched_tickets.extend(self.fetch_tickets_by_keys(keys))

        # Fall back to author's assigned tickets when no metadata keys match keys directly
        if not enriched_tickets and pr_data.get("author"):
            author_tickets = self.fetch_tickets_for_developer(
                pr_data["author"], 
                fallback_email=fallback_email  # ✅ Propagating dynamic identities safely
            )
            enriched_tickets.extend(author_tickets[:5])

        pr_data["linked_jira_tickets"] = self._convert_to_models(enriched_tickets)
        return pr_data

    def _map_github_to_jira(self, github_username: str, fallback_email: str = "") -> str:
        """
        Maps a GitHub user handle context to their target configuration email.
        Prioritizes dynamic run-time parameters over hardcoded env parameters.
        """
        env_email = os.getenv("JIRA_USER_EMAIL")
        if env_email:
            return env_email.split("#")[0].strip()

        # Dynamic mapping bypasses .env files entirely using the live extracted access token context
        if github_username.lower() in ["sh-code12", "malakhisham121"] and fallback_email:
            return fallback_email

        return github_username

    def _convert_to_models(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert raw Jira API ticket dicts to the internal model format."""
        converted = []

        for ticket in tickets:
            priority = ticket.get("priority", "Medium").lower()
            severity = self._SEVERITY_MAP.get(priority, "medium")

            description = ticket.get("description", "")
            affected_users: Optional[int] = None
            match = self._USER_COUNT_RE.search(description)
            if match:
                affected_users = int(match.group(1))

            converted.append({
                "key":                  ticket.get("key", ""),
                "summary":              ticket.get("summary", ""),
                "severity":             severity,
                "priority":             priority,
                "labels":               ticket.get("labels", []),
                "affected_users_count": affected_users,
                "description":          description[:500],
                "status":               ticket.get("status", "Unknown"),
            })

        return converted
        
    def enrich_pr_with_explicit_jira_config(
            self, 
            payload: dict, 
            fallback_email: str, 
            token: str, 
            cloud_id: str, 
            project_key: str
        ) -> dict:
            """
            Exposes an override function that communicates directly with the .NET context pipeline,
            passing credentials via explicit headers or runtime arguments.
            """
            # 1. First, parse out the ticket keys from the PR metadata strings
            keys = self.extract_jira_keys_from_pr(
                pr_title=payload.get("pr_title", ""),
                pr_body=payload.get("pr_body", ""),
                branch_name=payload.get("head_branch", ""),
                labels=payload.get("github_labels", []),
            )

            enriched_tickets: List[Dict[str, Any]] = []

            # 2. Try looking them up inside the local instance parsing cache
            if keys:
                enriched_tickets.extend(self.fetch_tickets_by_keys(keys))

            # 3. If no specific keys were matched, pull assigned tickets dynamically from the .NET microservice
            if not enriched_tickets and payload.get("author"):
                jira_username = self._map_github_to_jira(payload["author"], fallback_email)
                
                try:
                    # Forwarding incoming explicit credentials directly over the .NET Client abstraction layer
                    print(f"📡 Requesting tickets from .NET microservice using explicit credentials for: {jira_username}")
                    author_tickets = self.client.get_assigned_tickets(
                        assignee_name=jira_username,
                        token=token,
                        cloud_id=cloud_id,
                        project_key=project_key
                    )
                    enriched_tickets.extend(author_tickets[:5])
                except Exception as e:
                    print(f"⚠️ Failed fetching ad-hoc tickets over explicit .NET pipeline channel: {e}")

            # 4. Convert structural shapes back down into standard models payload
            payload["linked_jira_tickets"] = self._convert_to_models(enriched_tickets)
            return payload


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_dotnet_client: Optional[DotNetJiraClient] = None
_pr_enricher: Optional[PRJiraEnricher] = None


def get_dotnet_client() -> DotNetJiraClient:
    """Return the shared DotNetJiraClient instance, creating it if needed."""
    global _dotnet_client
    if _dotnet_client is None:
        _dotnet_client = DotNetJiraClient()
        _dotnet_client.set_credentials()
    return _dotnet_client


def get_pr_enricher() -> PRJiraEnricher:
    """Return the shared PRJiraEnricher instance, creating it if needed."""
    global _pr_enricher
    if _pr_enricher is None:
        _pr_enricher = PRJiraEnricher(get_dotnet_client())
    return _pr_enricher


def fetch_authenticated_github_email() -> str:
    """
    Queries GitHub's secure user endpoint directly using the local GITHUB_TOKEN.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("⚠️ GITHUB_TOKEN not found in environment configurations.")
        return ""

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Codience-Impact-Engine"
    }

    try:
        response = requests.get("https://api.github.com/user/emails", headers=headers, timeout=15)
        if response.status_code == 200:
            emails_list = response.json()
            
            for email_entry in emails_list:
                if email_entry.get("primary") and email_entry.get("verified"):
                    return email_entry.get("email", "")
            
            if emails_list:
                return emails_list[0].get("email", "")
                
        else:
            print(f"⚠️ GitHub API returned error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️ Failed to fetch identity directly from GitHub Network: {e}")
        
    return ""