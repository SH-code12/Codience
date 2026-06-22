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

FILE_DIFF_SUMMARY_PROMPT = """
You are a Senior Technical Architect analyzing a single file's changes.

FILE NAME: {filename}
DIFF:
{patch}

Task:
Summarize the technical changes made in this file in 1-2 sentences. 
Highlight any specific programming languages, frameworks, or libraries that are evident.
"""

COMMIT_CHUNK_SUMMARY_PROMPT = """
You are analyzing a developer's commit to understand their technical skills.

COMMIT MESSAGE: {commit_message}

FILE SUMMARIES:
{file_summaries}

Task:
Summarize the technical skills, languages, and frameworks demonstrated in this specific commit based on the files changed.
Keep it extremely concise (1-2 sentences).
"""

DEVELOPER_PROFILE_REDUCE_PROMPT = """
You are building a technical profile for a developer based on summaries of their recent commits.

DEVELOPER: {author}

COMMIT SUMMARIES:
{commit_summaries}

Task:
Identify the unique programming languages and technical skills this developer possesses.
Return a valid JSON array of strings representing their skills.
Example: ["Python", "React", "AWS", "SQL"]
"""
SENIORITY_SIGNALS_PROMPT = """
Analyze this PR text and identify if it contains any of these seniority signals:
- security (security fixes, auth, permissions, encryption, vulnerabilities)
- migration (database migrations, schema changes, data migration)
- performance (optimization, caching, indexing, query tuning)
- concurrency (threading, locks, async, parallel)
- refactoring (large structural changes, architecture)

PR TEXT:
{pr_text}

Return JSON only: {{"seniority_signals": ["signal1", "signal2"]}}
"""

MEANINGFUL_COMMIT_FILTER_PROMPT = """
You are an expert engineering manager. Analyze the following commit to determine if it provides meaningful evidence of a developer's technical skills (e.g., writing logic, designing architecture, fixing complex bugs).

Commit Message: {commit_message}
Files Modified: {filenames_str}

Is this a meaningful commit for skill profiling? 
Ignore trivial commits like "merge branch", typo fixes, or automated dependency updates.

Reply with EXACTLY ONE WORD: "YES" or "NO".
"""

JUDGE_EVALUATION_PROMPT = """
You are an expert Engineering Manager evaluating the proposed reviewers for a Pull Request.

PULL REQUEST DATA:
Title: {title}
Description: {description}

PROPOSED REVIEWERS:
{reviewers_text}

Task:
Evaluate whether this list of reviewers is acceptable and appropriate for the given PR. 
Consider their technical skills, historical relevance, and score justifications.
Are there obvious mismatches? Are the top reviewers actually qualified based on their skills and the PR's languages/skills?

Return your evaluation as a valid JSON object strictly matching this schema:
{{
    "accepted": true/false,
    "feedback": "string (If accepted, say 'Looks good'. If rejected, provide specific, actionable feedback to the recommendation agent on what to improve, e.g., 'Candidate X lacks Java skills but the PR is in Java. Please prioritize Java developers.')"
}}
"""