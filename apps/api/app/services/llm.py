"""LLM task extraction: build prompt context, call gpt-4o-mini, validate output."""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.db.client import get_db
from app.models.extraction import ExtractedTask

log = logging.getLogger(__name__)

# Canonical, P4-owned prompt. Single source of truth — loaded at runtime so a prompt
# edit takes effect without touching this module. Resolved relative to the repo root
# (apps/api/app/services/llm.py → parents[4] == repo root).
_PROMPT_PATH = Path(__file__).resolve().parents[4] / "prompts" / "task-extraction.md"

# Appended to the canonical doc to pin runtime behavior (the doc is written for the
# n8n era and describes orchestration steps the LLM should ignore).
_PROMPT_SUFFIX = """

---
RUNTIME INSTRUCTIONS (override any operational/n8n notes above):
- You are called programmatically. Return STRICT JSON ONLY — exactly the object in
  "## Output schema". No markdown, no prose, no code fences outside the JSON object.
- Ignore any instructions about n8n, drafts, or sending messages — those are handled
  by the backend, not by you. Your only job is to emit the JSON object.
"""


@lru_cache
def _system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8") + _PROMPT_SUFFIX


def get_active_projects(org_id: str) -> list[dict[str, Any]]:
    """Fetch active/planning projects with category names for the org.

    Categories are included intentionally for project disambiguation
    (e.g. "taller de nutrición" → Taller nutrición comunitaria).
    """
    db = get_db()
    result = (
        db.table("projects")
        .select("id, name, slug, status, project_categories(categories(name))")
        .eq("organization_id", org_id)
        .in_("status", ["planning", "active"])
        .order("name")
        .execute()
    )
    projects = []
    for row in result.data:
        categories = [
            pc["categories"]["name"]
            for pc in (row.get("project_categories") or [])
            if pc.get("categories")
        ]
        projects.append(
            {
                "id": row["id"],
                "name": row["name"],
                "slug": row["slug"],
                "categories": categories,
            }
        )
    return projects


def extract_task(
    message_body: str,
    sender_name: str,
    sender_phone: str,
    current_date: str,
    organization_name: str,
    organization_id: str,
    people_id: str,
    active_projects: list[dict[str, Any]],
) -> ExtractedTask:
    """Call gpt-4o-mini with the task-extraction prompt and validate the response."""
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    user_message = (
        f"Organization: {organization_name} (id: {organization_id})\n"
        f"Sender: {sender_name} (phone: {sender_phone}, people_id: {people_id})\n"
        f"Date: {current_date}\n"
        f"Active projects: {json.dumps(active_projects, ensure_ascii=False)}\n\n"
        f"Message: {message_body}"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content
    log.debug("LLM raw response: %s", raw)
    payload = json.loads(raw)
    return ExtractedTask.model_validate(payload)
