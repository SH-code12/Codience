import os
import requests
import json
import re
from dotenv import load_dotenv
from codience.src.Reviewer_Recommender.Process.llm import generate_with_resilience
from codience.src.Reviewer_Recommender.Process.prompts import JIRA_ANALYSIS_PROMPT
from pydantic import BaseModel, ValidationError

load_dotenv()

# ─── Configuration ────────────────────────────────────────────────────────────

JIRA_API_BASE_URL = os.getenv("JIRA_API_BASE_URL", "http://localhost:5051/api")


class JiraAnalysisOutput(BaseModel):
    domain: str
    recent_skills: list[str]
    summary: str


# ─── Jira API Client ──────────────────────────────────────────────────────────

class JiraClient:
    """
    Thin HTTP client for the .NET JiraController endpoints.

    Endpoints consumed:
      GET  /api/Jira/login              → Redirects to Atlassian OAuth flow
      GET  /api/Jira/callback?code=...  → Exchanges code for token + cloud info
      GET  /api/Jira/me?token=...       → Returns the current authenticated user
      POST /api/Jira/assigned-tickets   → Returns issues assigned to a user
    """

    def __init__(self, base_url: str = JIRA_API_BASE_URL, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── Auth ──────────────────────────────────────────────────────────────────

    def get_login_url(self) -> str:
        """
        Returns the Atlassian OAuth authorisation URL that the .NET backend
        would redirect to.  Useful when you need to show the URL to a user
        rather than following the redirect automatically.
        """
        return f"{self.base_url}/Jira/login"

    def exchange_code_for_token(self, code: str) -> dict:
        """
        Calls GET /api/Jira/callback?code=<code> and returns the full JSON
        response which includes { accessToken, cloudId, Projects }.
        """
        url = f"{self.base_url}/Jira/callback"
        response = requests.get(url, params={"code": code}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_current_user(self, token: str) -> dict:
        """
        Calls GET /api/Jira/me?token=<token> and returns the user object.
        """
        url = f"{self.base_url}/Jira/me"
        response = requests.get(url, params={"token": token}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    # ── Issues ────────────────────────────────────────────────────────────────

    def get_assigned_tickets(
        self,
        token: str,
        cloud_id: str,
        project_key: str,
        assignee_name: str,
    ) -> list[dict]:
        """
        Calls POST /api/Jira/assigned-tickets and returns the list of issues.

        Matches the JiraRequestDto expected by the controller:
          { Token, CloudId, ProjectKey, AssigneeName }
        """
        url = f"{self.base_url}/Jira/assigned-tickets"
        payload = {
            "token": token,
            "cloudId": cloud_id,
            "projectKey": project_key,
            "assigneeName": assignee_name,
        }
        response = requests.post(url, json=payload, timeout=self.timeout)
        if not response.ok:
            print(f"⚠️ Jira API Error Response Body: {response.text}")
        response.raise_for_status()
        return response.json()


# ─── Default client (uses env config) ────────────────────────────────────────

_client = JiraClient()


# ─── Public helpers ───────────────────────────────────────────────────────────

# Use this to map GitHub usernames to Jira display names/Account IDs if they differ.
GITHUB_TO_JIRA_MAPPING = {
    # "github_username": "Jira Display Name",
    "your_github_username": "Your Jira Name", 
}

def _resolve_jira_name(github_username: str) -> str:
    """Resolves a GitHub username to a Jira username using the local mapping."""
    # If the user is in the mapping, use the mapped name. Otherwise, fallback to github username.
    return GITHUB_TO_JIRA_MAPPING.get(github_username, github_username)

# This API should recieve data from frontend and then return the tickets
def fetch_jira_tickets(
    username: str,
    jira_username: str = None,
    token: str = None,
    cloud_id: str = None,
    project_key: str = None,
) -> list[dict]:
    # ─── DEBUG SECTION ───
    print(f"🔍 DEBUG: Resolving Jira identity for {username}")
    
    # This data should be passed from frontend or backend
    target_user = jira_username or os.getenv("JIRA_USERNAME", username)
    resolved_token = token or os.getenv("JIRA_API_TOKEN")
    resolved_cloud_id = cloud_id or os.getenv("JIRA_CLOUD_ID")
    resolved_project_key = project_key or os.getenv("JIRA_PROJECT_KEY")

    print(f"   -> Target User: {target_user}")
    print(f"   -> Token exists: {bool(resolved_token)}")
    print(f"   -> Cloud ID exists: {bool(resolved_cloud_id)}")
    print(f"   -> Project Key exists: {bool(resolved_project_key)}")

    # Check for None values - C# will reject these with a 400 error!
    if not all([resolved_token, resolved_cloud_id, resolved_project_key]):
        print("❌ ERROR: Missing required Jira credentials in .env or API request.")
        return []

    try:
        tickets = _client.get_assigned_tickets(
            token=resolved_token,
            cloud_id=resolved_cloud_id,
            project_key=resolved_project_key,
            assignee_name=target_user,
        )
        return tickets
    except requests.exceptions.ConnectionError:
        print("⚠️ Jira server unreachable (Connection refused). Skipping Jira context.")
        return []
    except Exception as exc:
        print(f"⚠️ Jira Error: {type(exc).__name__}. Skipping Jira context.")
        return []


def get_current_user(token: str = None) -> dict:
    """
    Returns the Jira user profile for the supplied (or env-based) token
    by calling GET /api/Jira/me.
    """
    resolved_token = token or os.getenv("JIRA_API_TOKEN", "")
    try:
        user = _client.get_current_user(resolved_token)
        return user
    except requests.HTTPError as http_err:
        print(f"⚠️  HTTP error fetching current Jira user: {http_err}")
    except requests.RequestException as req_err:
        print(f"⚠️  Network error fetching current Jira user: {req_err}")
    except Exception as exc:
        print(f"⚠️  Unexpected error fetching current Jira user: {exc}")
    return {}


# ─── LLM Analysis ─────────────────────────────────────────────────────────────

def analyze_jira_context(
    username: str,
    jira_username: str = None,
    token: str = None,
    cloud_id: str = None,
    project_key: str = None,
) -> dict:
    """
    Fetches Jira tickets for *username* and uses the configured LLM to
    determine the developer's current domain and skills.

    Returns a dict with keys: domain, recent_skills, summary.
    """
    tickets = fetch_jira_tickets(
        username,
        jira_username=jira_username,
        token=token,
        cloud_id=cloud_id,
        project_key=project_key,
    )
    return analyze_jira_tickets(username, tickets)


def analyze_jira_tickets(username: str, tickets: list[dict]) -> dict:
    """
    Uses the configured LLM to determine the developer's current domain and skills
    from the provided list of tickets.
    """


    if not tickets:
        return {"domain": "Unknown", "recent_skills": [], "summary": "No Jira tickets found."}

    # Build a text representation for the LLM (cap at 10 tickets)
    ticket_texts: list[str] = []
    for i, ticket in enumerate(tickets[:10]):
        title = ticket.get("title") or ticket.get("summary", "")
        description = ticket.get("description", "")
        if not title and not description:
            continue
        ticket_texts.append(f"Ticket {i + 1}: TITLE: {title}\nDESCRIPTION: {description}")

    if not ticket_texts:
        return {"domain": "Unknown", "recent_skills": [], "summary": "No valid Jira ticket content found."}

    combined_tickets = "\n\n".join(ticket_texts)
    prompt = JIRA_ANALYSIS_PROMPT.format(username=username, combined_tickets=combined_tickets)

    result = generate_with_resilience(prompt, purpose="jira_analysis")
    if not result.get("ok"):
        print(f"⚠️  Jira analysis fallback for '{username}'. reason={result.get('reason')}")
        return {"domain": "Unknown", "recent_skills": [], "summary": "Analysis failed after retries."}

    raw_text = result.get("text", "")
    try:
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        json_str = json_match.group() if json_match else raw_text
        parsed_data = json.loads(json_str)
        validated_output = JiraAnalysisOutput(**parsed_data)
        return validated_output.model_dump()
    except json.JSONDecodeError as decode_error:
        print(f"⚠️  Jira JSON decode error: {decode_error}")
    except ValidationError as validation_error:
        print(f"⚠️  Jira validation failed: {validation_error}")
    except Exception as exc:
        print(f"⚠️  Jira analysis parse error: {exc}")

    return {"domain": "Unknown", "recent_skills": [], "summary": "Analysis failed after retries."}


# ─── Smoke test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = analyze_jira_context("test_user")
    print("\n--- Jira Analysis Output ---")
    print(json.dumps(result, indent=2))