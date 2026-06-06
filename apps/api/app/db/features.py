"""Runtime detection of optional schema capabilities."""

from __future__ import annotations

import logging
from typing import Any

from postgrest.exceptions import APIError

log = logging.getLogger(__name__)

_confirmation_gate: bool | None = None


def confirmation_gate_enabled(db: Any) -> bool:
    """True when migration 002 (WhatsApp confirmation gate) is applied."""
    global _confirmation_gate
    if _confirmation_gate is not None:
        return _confirmation_gate

    try:
        db.table("task_drafts").select("resolved_task").limit(0).execute()
        db.table("task_drafts").select("id").eq("status", "awaiting_confirmation").limit(0).execute()
        _confirmation_gate = True
    except APIError as exc:
        message = str(exc)
        if "resolved_task does not exist" in message or "awaiting_confirmation" in message:
            log.warning(
                "Confirmation gate schema missing — apply database/migrations/002_confirmation_gate.sql "
                "in Supabase SQL editor. Falling back to immediate task insert."
            )
            _confirmation_gate = False
        else:
            raise

    return _confirmation_gate


def reset_confirmation_gate_cache() -> None:
    """Test helper — clear the cached schema probe."""
    global _confirmation_gate
    _confirmation_gate = None
