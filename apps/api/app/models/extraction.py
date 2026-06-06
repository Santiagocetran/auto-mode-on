"""Pydantic models mirroring the task-extraction.md output schema.

scope_reason and several project_resolution fields are Optional because the
prompt's examples don't uniformly include them (e.g. example A omits scope_reason).
Strict-required would reject otherwise-valid LLM outputs.
"""

from typing import Literal, Optional

from pydantic import BaseModel


class ProjectResolution(BaseModel):
    status: Literal["matched", "standalone", "needs_clarification", "not_applicable"]
    project_id: Optional[str] = None
    project_name_matched: Optional[str] = None
    confidence: float
    reason: str


class ExtractedTask(BaseModel):
    intent: str
    owner: str
    task_title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: Literal["pending", "in_progress", "blocked", "done", "cancelled"] = "pending"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    confidence: float
    is_global: bool
    project_resolution: ProjectResolution
    scope_reason: Optional[str] = None
    ambiguities: list[str] = []
