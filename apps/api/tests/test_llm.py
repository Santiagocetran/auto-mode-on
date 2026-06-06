"""Tests for app.services.llm prompt sourcing (no live API calls)."""

from app.services.llm import _PROMPT_PATH, _system_prompt


def test_canonical_prompt_file_exists():
    # The prompt is P4-owned and must be loaded from the repo, not inlined.
    assert _PROMPT_PATH.exists(), f"canonical prompt missing at {_PROMPT_PATH}"
    assert _PROMPT_PATH.name == "task-extraction.md"


def test_system_prompt_loads_canonical_content_and_runtime_suffix():
    prompt = _system_prompt()
    # Content from the canonical doc…
    assert "Output schema" in prompt
    assert "needs_clarification" in prompt
    # …plus the runtime override that pins JSON-only behavior.
    assert "STRICT JSON ONLY" in prompt
