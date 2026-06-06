"""Org and sender resolution from Twilio webhook fields.

Phone-format contract (from data model):
- organization_channels.whatsapp_number stores "whatsapp:+E164"
- people.whatsapp_number stores "+E164" (no prefix)
- Twilio From/To arrive as "whatsapp:+E164"
- inbound_messages.sender_phone is stored as "+E164" (people-compatible)
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.db.client import get_db

log = logging.getLogger(__name__)


@dataclass
class Org:
    id: str
    name: str
    channel_id: str


@dataclass
class Person:
    id: str
    display_name: str
    whatsapp_number: str  # +E164 form (no prefix)
    user_id: Optional[str]


def normalize_twilio_whatsapp(value: str) -> str:
    """Ensure value is in 'whatsapp:+E164' form (for channel matching and Twilio sends)."""
    if not value.startswith("whatsapp:"):
        return f"whatsapp:{value}"
    return value


def strip_whatsapp_prefix(value: str) -> str:
    """Strip 'whatsapp:' prefix, returning '+E164' (for people table matching)."""
    if value.startswith("whatsapp:"):
        return value[len("whatsapp:"):]
    return value


def resolve_org(to_number: str) -> Optional[Org]:
    """Resolve organization from Twilio To field.

    Keeps the whatsapp: prefix for matching against organization_channels.
    Returns None if no active channel matches.
    """
    normalized = normalize_twilio_whatsapp(to_number)
    db = get_db()
    result = (
        db.table("organization_channels")
        .select("id, organization_id, organizations(id, name)")
        .eq("whatsapp_number", normalized)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not result.data:
        log.debug("No active channel for To=%s", normalized)
        return None
    row = result.data[0]
    org_row = row["organizations"]
    return Org(
        id=org_row["id"],
        name=org_row["name"],
        channel_id=row["id"],
    )


def resolve_sender(org_id: str, from_number: str) -> Optional[Person]:
    """Resolve sender from the people table.

    Strips the whatsapp: prefix before matching, since people.whatsapp_number
    stores plain +E164. Channel-first: org_id scopes the lookup so the same
    phone in two orgs resolves to the correct one.
    """
    phone = strip_whatsapp_prefix(from_number)
    db = get_db()
    result = (
        db.table("people")
        .select("id, display_name, whatsapp_number, user_id")
        .eq("organization_id", org_id)
        .eq("whatsapp_number", phone)
        .limit(1)
        .execute()
    )
    if not result.data:
        log.debug("No people row for org=%s phone=%s", org_id, phone)
        return None
    row = result.data[0]
    return Person(
        id=row["id"],
        display_name=row["display_name"],
        whatsapp_number=row["whatsapp_number"],
        user_id=row.get("user_id"),
    )
