SKILL_EXTRACTION_PROMPT = """
You are a Senior Technical Architect. Your task is to analyze a Pull Request and identify the specific technical skills and programming languages required to audit this code.

PR DATA:
Title: {title}
Description: {description}
Code Changes (Diff):
{diff}

INSTRUCTIONS:
1. **Identify Atomic Technical Skills**: Be specific to libraries and logic (e.g., "FastAPI: Dependency Injection", "OpenCV: Image Thresholding").
2. **Identify Raw Programming Languages**: List the base programming languages involved (e.g., "Python", "Java", "C#", "SQL").
3. **Format**: Extract skills as 'Technology: Specific Feature'.
4. **Prioritize**: Highlight high-risk logic like security or database migrations.

OUTPUT FORMAT (JSON ONLY):
{{
  "required_skills": ["Skill A", "Skill B"],
  "detected_languages": ["Language A", "Language B"],
  "rag_query": "A Senior Engineer with expertise in [Key Skills] and [Languages]."
}}
"""

JIRA_ANALYSIS_PROMPT = """
You are an AI tasked with analyzing a developer's recently assigned Jira tickets to understand their current technical domain and skills.

DEVELOPER USERNAME: {username}

RECENT TICKETS:
{combined_tickets}

Task:
Based on the tickets, identify the primary domain the developer is working on (e.g., Authentication, Database Migration, Frontend UI, CI/CD) and the specific technical skills or tools that are apparent from the ticket contents.

Return the response as a valid JSON object strictly matching this schema:
{{
    "domain": "string (the current primary work domain)",
    "recent_skills": ["skill_1", "skill_2"],
    "summary": "string (1-2 sentence summary of their recent focus)"
}}
"""

SCORER_PROMPT = """
You are an expert tech lead tasked with assigning the best reviewers for a Pull Request.

PULL REQUEST REQUIREMENTS:
- Required Skills: {pr_skills} 
- Analysis Summary: {pr_analysis_summary} 

VECTOR DATABASE RECOMMENDATIONS (Historical Best Roles):
{rag_context}

CANDIDATES PROFILES:
{candidates_text}

Task:
Rank ALL candidates based on how well their historical commit skills and current Jira domain match the PR requirements. 
Assign each a 'confidence_score' from 0 to 100, where 100 is an absolutely perfect match and 0 is no relevance at all.
Also provide a short 1-sentence 'justification' for why they received this score.

Output strictly in the following JSON array format:
[
    {{
        "name": "Candidate Name",
        "confidence_score": 85,
        "justification": "Has strong recent Jira activity in the required domain and commit history matches perfectly."
    }}
]
"""