"""Resolve canonical prompt files for local dev and Docker."""

from pathlib import Path

_PROMPT_NAME = "task-extraction.md"


def task_extraction_prompt_path() -> Path:
    """Return prompts/task-extraction.md from repo root or /app in Docker."""
    here = Path(__file__).resolve()
    for base in here.parents:
        path = base / "prompts" / _PROMPT_NAME
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"prompts/{_PROMPT_NAME} not found (searched from {here})"
    )
