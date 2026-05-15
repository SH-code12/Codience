import json
import re
from typing import List, Dict, Any
from pydantic import BaseModel, ValidationError
from codience.src.Reviewer_Recommender.Process.llm import generate_with_resilience
from codience.src.Reviewer_Recommender.Process.prompts import SCORER_PROMPT



class CandidateScore(BaseModel):
    name: str
    confidence_score: int
    justification: str

def calculate_match_scores(pr_analysis: Dict[str, Any], rag_roles: List[Dict[str, Any]], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates a list of candidates against PR requirements and their Jira/Commit context.
    Returns a ranked list with a 0 to 100 confidence score.
    
    pr_analysis: output from extract_pr_skills
    rag_roles: list of recommended roles from search_vector_db (if available)
    candidates: list of dicts: 
        [{"name": "DevA", "commit_skills": ["Python"], "jira_context": {"domain": "...", "recent_skills": []}}]
    """
    
    if not candidates:
        return []
        
    # Format candidates for the prompt
    candidates_text = ""
    for i, c in enumerate(candidates):
        c_name = c["name"]
        c_commits = ", ".join(c.get("commit_skills", []))
        c_jira_domain = c.get("jira_context", {}).get("domain", "Unknown")
        c_jira_skills = ", ".join(c.get("jira_context", {}).get("recent_skills", []))
        c_raw_skills = ", ".join(c.get("raw_skills", [])) if isinstance(c.get("raw_skills"), list) else c.get("raw_skills", "None")
        
        candidates_text += f"\nCandidate {i+1}: {c_name}\n"
        candidates_text += f" - Commit History Skills: {c_commits}\n"
        candidates_text += f" - Current Jira Domain: {c_jira_domain}\n"
        candidates_text += f" - Recent Jira Skills: {c_jira_skills}\n"
        candidates_text += f" - Explicitly Provided Skills: {c_raw_skills}\n"

    # Format PR and RAG context
    pr_skills = ", ".join(pr_analysis.get("required_skills", pr_analysis.get("detected_languages", [])))
    rag_context = "\n".join([f"- {r.page_content}" for r in rag_roles]) if rag_roles else "No specific role found in Vector DB."

    prompt = SCORER_PROMPT.format(
        pr_skills=pr_skills,
        pr_analysis_summary=pr_analysis.get("summary", ""),
        rag_context=rag_context,
        candidates_text=candidates_text
    )
    
    result = generate_with_resilience(prompt, purpose="candidate_scoring")
    if result.get("ok"):
        raw_text = result.get("text", "")
        try:
            json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            json_str = json_match.group() if json_match else raw_text
            parsed_data = json.loads(json_str)
            validated_results = []
            for item in parsed_data:
                validated_results.append(CandidateScore(**item).model_dump())

            return sorted(validated_results, key=lambda x: x.get("confidence_score", 0), reverse=True)
        except json.JSONDecodeError as decode_error:
            print(f"⚠️ Scorer JSON decode error: {decode_error}")
        except ValidationError as validation_error:
            print(f"⚠️ Scorer validation failed: {validation_error}")
        except Exception as e:
            print(f"⚠️ Scorer parse error: {e}")
    else:
        print(f"⚠️ Scorer LLM fallback. reason={result.get('reason')}")

    # Fallback heuristic if all retries fail
    print("⚠️ Heuristic scorer fallback used.")
    fallback_results = []
    req_set = set(pr_analysis.get("detected_languages", []))
    for c in candidates:
        c_skills = set(c.get("commit_skills", []))
        match_count = len(req_set.intersection(c_skills))
        score = min(100, int((match_count / max(len(req_set), 1)) * 100))
        fallback_results.append({
            "name": c["name"],
            "confidence_score": score,
            "justification": "Fallback heuristic used due to LLM error."
        })
    return sorted(fallback_results, key=lambda x: x["confidence_score"], reverse=True)
