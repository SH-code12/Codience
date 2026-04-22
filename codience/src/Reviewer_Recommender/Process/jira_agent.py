import os
import requests
import json
import re
from dotenv import load_dotenv
from codience.src.Reviewer_Recommender.Process.llm import generate_with_resilience
from codience.src.Reviewer_Recommender.Process.prompts import JIRA_ANALYSIS_PROMPT
from pydantic import BaseModel, ValidationError

class JiraAnalysisOutput(BaseModel):
    domain: str
    recent_skills: list[str]
    summary: str

load_dotenv()

# Suppose the .NET API base URL is stored in an env variable, falling back to localhost for tests
JIRA_API_BASE_URL = os.getenv("JIRA_API_BASE_URL", "http://localhost:5000/api")
JIRA_API_MOCK = os.getenv("JIRA_API_MOCK", "false").lower() == "true"
JIRA_API_MOCK_ON_FAILURE = os.getenv("JIRA_API_MOCK_ON_FAILURE", "true").lower() == "true"


def _build_mock_tickets(username: str):
    return [
        {
            "title": f"Refactor reviewer ranking pipeline for {username}",
            "description": "Optimize scoring logic, add retries, and improve fallback behavior for API outages.",
            "status": "In Progress",
        },
        {
            "title": "Improve FastAPI endpoint latency",
            "description": "Reduce request overhead and improve payload validation for recommendation endpoints.",
            "status": "Done",
        },
        {
            "title": "Stabilize vector DB search quality",
            "description": "Tune embeddings retrieval and improve relevance for role suggestions.",
            "status": "To Do",
        },
    ]

def fetch_jira_tickets(username: str, jira_username: str = None):
    """
    Fetches Jira tickets assigned to the given user from the existing .NET backend.
    If jira_username is provided, it is used instead of the repository username.
    """
    target_user = jira_username if jira_username else username
    
    if JIRA_API_MOCK:
        print(f"ℹ️ Using mocked Jira tickets for {target_user}.")
        return _build_mock_tickets(target_user)

    url = f"{JIRA_API_BASE_URL}/tickets/{target_user}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ Failed to fetch Jira tickets for {target_user}. Status: {response.status_code}")
            if JIRA_API_MOCK_ON_FAILURE:
                print(f"ℹ️ Falling back to mocked Jira tickets for {target_user}.")
                return _build_mock_tickets(target_user)
            return []
    except Exception as e:
        print(f"⚠️ Error fetching Jira tickets for {target_user} from .NET API: {e}")
        if JIRA_API_MOCK_ON_FAILURE:
            print(f"ℹ️ Falling back to mocked Jira tickets for {target_user}.")
            return _build_mock_tickets(target_user)
        return []

def analyze_jira_context(username: str, jira_username: str = None):
    """
    Fetches and analyzes Jira tickets for a user using the configured LLM provider to determine current domain and skills.
    """
    tickets = fetch_jira_tickets(username, jira_username=jira_username)
    
    if not tickets:
        return {"domain": "Unknown", "recent_skills": [], "summary": "No Jira tickets found."}

    # Format ticket info for the LLM
    # Assuming tickets have 'title', 'description', and 'status' (or similar structure)
    ticket_texts = []
    for i, t in enumerate(tickets[:10]): # Analyze at most 10 recent tickets
        title = t.get("title", "") or t.get("summary", "")
        desc = t.get("description", "")
        if not title and not desc:
            continue
        ticket_texts.append(f"Ticket {i+1}: TITLE: {title}\nDESCRIPTION: {desc}")
    
    if not ticket_texts:
        return {"domain": "Unknown", "recent_skills": [], "summary": "No valid Jira ticket content found."}
    
    combined_tickets = "\n\n".join(ticket_texts)

    prompt = JIRA_ANALYSIS_PROMPT.format(username=username, combined_tickets=combined_tickets)
    
    result = generate_with_resilience(prompt, purpose="jira_analysis")
    if not result.get("ok"):
        print(f"⚠️ Jira analysis fallback for {username}. reason={result.get('reason')}")
        return {"domain": "Unknown", "recent_skills": [], "summary": "Analysis failed after retries."}

    raw_text = result.get("text", "")
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        json_str = json_match.group() if json_match else raw_text
        parsed_data = json.loads(json_str)
        validated_output = JiraAnalysisOutput(**parsed_data)
        return validated_output.model_dump()
    except json.JSONDecodeError as decode_error:
        print(f"⚠️ Jira JSON decode error: {decode_error}")
    except ValidationError as validation_error:
        print(f"⚠️ Jira validation failed: {validation_error}")
    except Exception as e:
        print(f"⚠️ Jira analysis parse error: {e}")

    return {"domain": "Unknown", "recent_skills": [], "summary": "Analysis failed after retries."}

if __name__ == "__main__":
    # Test execution
    res = analyze_jira_context("test_user")
    print("\n--- Test Jira Analysis Output ---")
    print(json.dumps(res, indent=2))
