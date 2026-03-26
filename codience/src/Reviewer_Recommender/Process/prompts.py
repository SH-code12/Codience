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