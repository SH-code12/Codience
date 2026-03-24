from pydantic import BaseModel, Field
from typing import List, Optional

class Reviewer(BaseModel):
    name: str = Field(description="Name or username of the reviewer")
    skills: List[str] = Field(description="List of technical skills extracted")
    active_jira_tickets: int = Field(default=0, description="Number of currently assigned tickets")
    recent_commits: List[str] = Field(default=[], description="Recent file paths touched in GitHub")