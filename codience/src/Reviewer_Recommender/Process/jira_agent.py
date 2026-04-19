import os
import requests
import json
import re
from dotenv import load_dotenv
from codience.src.Reviewer_Recommender.Process.llm import get_model
from codience.src.Reviewer_Recommender.Process.prompts import JIRA_ANALYSIS_PROMPT
from pydantic import BaseModel, ValidationError

class JiraAnalysisOutput(BaseModel):
    domain: str
    recent_skills: list[str]
    summary: str

load_dotenv()

# Suppose the .NET API base URL is stored in an env variable, falling back to localhost for tests
JIRA_API_BASE_URL = os.getenv("JIRA_API_BASE_URL", "http://localhost:5000/api")

def fetch_jira_tickets(username: str):
    """
    Fetches Jira tickets assigned to the given user from the existing .NET backend.
    """
    url = f"{JIRA_API_BASE_URL}/tickets/{username}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ Failed to fetch Jira tickets for {username}. Status: {response.status_code}")
            return []
    except Exception as e:
        print(f"⚠️ Error fetching Jira tickets for {username} from .NET API: {e}")
        return []

def analyze_jira_context(username: str):
    """
    Fetches and analyzes Jira tickets for a user using Gemini to determine their current domain and skills.
    """
    tickets = fetch_jira_tickets(username)
    
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
    
    client = get_model()
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=prompt
            )
            
            raw_text = response.text
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            json_str = json_match.group() if json_match else raw_text
            
            # Strict Validation using Pydantic
            parsed_data = json.loads(json_str)
            validated_output = JiraAnalysisOutput(**parsed_data)
            return validated_output.model_dump()
            
        except json.JSONDecodeError as decode_error:
            print(f"⚠️ Attempt {attempt + 1}: JSON decode error: {decode_error}")
        except ValidationError as validation_error:
            print(f"⚠️ Attempt {attempt + 1}: Pydantic validation failed: {validation_error}")
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1}: Unexpected LLM error: {e}")
            
    # Fallback default state
    print(f"⚠️ All {max_retries} attempts failed for analyzing Jira tickets for {username}.")
    return {"domain": "Unknown", "recent_skills": [], "summary": "Analysis failed after retries."}

if __name__ == "__main__":
    # Test execution
    res = analyze_jira_context("test_user")
    print("\n--- Test Jira Analysis Output ---")
    print(json.dumps(res, indent=2))
