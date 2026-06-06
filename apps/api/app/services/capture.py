"""WhatsApp capture pipeline orchestration.

Flow (per plan):
  1. Resolve org (To → organization_channels) — security gate
  2. Save inbound_messages (idempotent by MessageSid)
  3. Resolve sender (From → people scoped to org) — security gate
  4. Pending-draft branch (reply to disambiguation menu)
  5. LLM extraction + scope branching
"""

import logging
import unicodedata
from typing import Any, Optional

from app.config import get_settings
from app.db.client import get_db
from app.db.features import confirmation_gate_enabled
from app.models.extraction import ExtractedTask
from app.services import llm, resolution, transcription
from app.services.resolution import Org, Person, normalize_twilio_whatsapp, strip_whatsapp_prefix
from app.services.twilio_client import send_whatsapp

log = logging.getLogger(__name__)


def handle_inbound(form_data: dict) -> None:
    """Main entry point called by the router after signature validation."""
    to_number = form_data.get("To", "")
    from_number = form_data.get("From", "")
    body = form_data.get("Body", "") or ""
    profile_name = form_data.get("ProfileName") or ""
    message_sid = form_data.get("MessageSid") or ""

    # 1. Resolve org — security gate (before saving anything)
    org = resolution.resolve_org(to_number)
    if org is None:
        log.warning("Unknown channel: To=%s — dropping message", to_number)
        return

    db = get_db()
    confirmation = confirmation_gate_enabled(db)
    sender_phone_e164 = strip_whatsapp_prefix(from_number)

    # 2. Idempotent inbound save
    inbound_id, is_replay = _save_inbound(
        db=db,
        org_id=org.id,
        message_sid=message_sid,
        sender_phone=sender_phone_e164,
        sender_name=profile_name,
        body=body,
        raw_payload=dict(form_data),
    )
    if is_replay:
        log.info("Replay detected for MessageSid=%s — short-circuiting", message_sid)
        return

    # 3. Resolve sender — security gate
    person = resolution.resolve_sender(org.id, from_number)
    reply_to = normalize_twilio_whatsapp(from_number)
    if person is None:
        log.info("Unregistered sender %s in org %s", sender_phone_e164, org.id)
        send_whatsapp(reply_to, "No estás registrado en esta organización. Contactá al administrador.")
        return

    # 3b. Normalize the message to text — transcribe audio voice notes. Done after
    # the sender gate so we never spend a transcription on an unregistered number.
    settings = get_settings()
    try:
        message_text = transcription.normalize_message(form_data, settings)
    except transcription.MessageNormalizationError:
        log.info("Unparseable message from %s (no text / unsupported media)", sender_phone_e164)
        send_whatsapp(reply_to, "No pude entender el mensaje. Si enviaste un audio, probá de nuevo o escribilo por texto.")
        return
    except transcription.TranscriptionError:
        log.exception("Audio transcription failed for org=%s", org.id)
        send_whatsapp(reply_to, "No pude transcribir el audio. ¿Podés escribirlo por texto?")
        return

    if message_text != body:
        # Audio was transcribed (or body normalized) — persist the resolved text + media URL.
        body = message_text
        db.table("inbound_messages").update(
            {"body": body, "media_url": form_data.get("MediaUrl0")}
        ).eq("id", inbound_id).execute()

    # 4. Pending-conversation branch — a draft awaiting either a project choice
    #    or a si/no confirmation. Resolve it before running a fresh extraction so
    #    replies like "si" are never mistaken for a new task.
    pending_select = "id, status, extraction_payload, offered_projects, source_message_id"
    pending_statuses = ["awaiting_project_choice"]
    if confirmation:
        pending_select += ", resolved_task"
        pending_statuses.append("awaiting_confirmation")

    pending = (
        db.table("task_drafts")
        .select(pending_select)
        .eq("organization_id", org.id)
        .eq("sender_phone", sender_phone_e164)
        .in_("status", pending_statuses)
        .limit(1)
        .execute()
    )
    if pending.data:
        draft_row = pending.data[0]
        if confirmation and draft_row.get("status") == "awaiting_confirmation":
            _handle_confirmation_reply(
                db=db,
                draft_row=draft_row,
                reply_text=body,
                reply_to=reply_to,
            )
        else:
            _handle_draft_reply(
                db=db,
                draft_row=draft_row,
                reply_text=body,
                org=org,
                person=person,
                sender_phone=sender_phone_e164,
                reply_to=reply_to,
                confirmation=confirmation,
            )
        return

    # 5. Run extraction
    active_projects = llm.get_active_projects(org.id)
    from datetime import date
    try:
        extracted = llm.extract_task(
            message_body=body,
            sender_name=person.display_name,
            sender_phone=sender_phone_e164,
            current_date=date.today().isoformat(),
            organization_name=org.name,
            organization_id=org.id,
            people_id=person.id,
            active_projects=active_projects,
        )
    except Exception:
        log.exception("LLM extraction failed for org=%s", org.id)
        send_whatsapp(reply_to, "Hubo un error procesando tu mensaje. Por favor intentá de nuevo.")
        return

    # Low confidence with a non-clarification result → ask to rephrase
    if extracted.confidence < 0.6 and extracted.project_resolution.status != "needs_clarification":
        send_whatsapp(reply_to, "No entendí bien el pedido. ¿Podés reformularlo con más detalle?")
        return

    owner_id, owner_name = _map_owner(db, extracted.owner, org.id, person)
    pr_status = extracted.project_resolution.status

    if extracted.is_global:
        _handle_global(
            db=db,
            extracted=extracted,
            org=org,
            person=person,
            owner_id=owner_id,
            owner_name=owner_name,
            inbound_id=inbound_id,
            body=body,
            reply_to=reply_to,
            sender_phone=sender_phone_e164,
            confirmation=confirmation,
        )
        return

    if pr_status == "needs_clarification":
        _insert_draft_and_ask(
            db=db,
            extracted=extracted,
            org=org,
            person=person,
            sender_phone=sender_phone_e164,
            inbound_id=inbound_id,
            active_projects=active_projects,
            reply_to=reply_to,
        )
        return

    if pr_status == "matched":
        project_id = extracted.project_resolution.project_id
        valid_ids = {p["id"] for p in active_projects}
        if not project_id or project_id not in valid_ids:
            log.warning(
                "Matched project_id=%s not in active snapshot — escalating to clarify",
                project_id,
            )
            _insert_draft_and_ask(
                db=db,
                extracted=extracted,
                org=org,
                person=person,
                sender_phone=sender_phone_e164,
                inbound_id=inbound_id,
                active_projects=active_projects,
                reply_to=reply_to,
            )
            return
        _insert_task(
            db=db,
            extracted=extracted,
            org=org,
            project_id=project_id,
            is_global=False,
            owner_id=owner_id,
            owner_name=owner_name,
            inbound_id=inbound_id,
            source_text=body,
            reply_to=reply_to,
            person=person,
            sender_phone=sender_phone_e164,
            confirmation=confirmation,
        )
        return

    if pr_status == "standalone":
        _insert_task(
            db=db,
            extracted=extracted,
            org=org,
            project_id=None,
            is_global=False,
            owner_id=owner_id,
            owner_name=owner_name,
            inbound_id=inbound_id,
            source_text=body,
            reply_to=reply_to,
            person=person,
            sender_phone=sender_phone_e164,
            confirmation=confirmation,
        )
        return

    log.error("Unexpected project_resolution.status=%s for org=%s", pr_status, org.id)


# ---------------------------------------------------------------------------
# Helpers (all receive db explicitly — easier to test and no repeated get_db calls)
# ---------------------------------------------------------------------------


def _save_inbound(
    db,
    org_id: str,
    message_sid: str,
    sender_phone: str,
    sender_name: str,
    body: str,
    raw_payload: dict,
) -> tuple[Optional[str], bool]:
    """Insert inbound_messages row, returning (id, is_replay).

    On unique-constraint collision (same MessageSid) → fetch existing row and
    return (existing_id, True) so the caller can short-circuit.
    """
    try:
        result = (
            db.table("inbound_messages")
            .insert(
                {
                    "organization_id": org_id,
                    "provider": "twilio",
                    "provider_message_id": message_sid or None,
                    "sender_phone": sender_phone,
                    "sender_name": sender_name or None,
                    "body": body,
                    "raw_payload": raw_payload,
                }
            )
            .execute()
        )
        return result.data[0]["id"], False
    except Exception as exc:
        # Almost certainly a unique-constraint violation on (org, provider, MessageSid).
        # If MessageSid is missing we treat it as a distinct message (NULL != NULL in PG).
        if message_sid:
            existing = (
                db.table("inbound_messages")
                .select("id")
                .eq("organization_id", org_id)
                .eq("provider", "twilio")
                .eq("provider_message_id", message_sid)
                .limit(1)
                .execute()
            )
            if existing.data:
                return existing.data[0]["id"], True
        log.exception("Failed to save inbound message: %s", exc)
        return None, False


def _can_create_global(db, org_id: str, person: Person) -> bool:
    """Return True only when the person's role grants can_create_global_tasks."""
    if not person.user_id:
        # WhatsApp-only person (null user_id) → no provable membership → conservative path
        return False

    membership = (
        db.table("organization_memberships")
        .select("role")
        .eq("organization_id", org_id)
        .eq("user_id", person.user_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    if not membership.data:
        return False

    role = membership.data[0]["role"]

    settings_result = (
        db.table("organization_settings")
        .select("role_permissions")
        .eq("organization_id", org_id)
        .limit(1)
        .execute()
    )
    if not settings_result.data:
        return False

    role_permissions = settings_result.data[0].get("role_permissions", {})
    return bool(role_permissions.get(role, {}).get("can_create_global_tasks", False))


def _map_owner(
    db, owner_str: str, org_id: str, sender: Person
) -> tuple[Optional[str], str]:
    """Map LLM owner string to (owner_id, owner_name).

    "yo" / "me encargo" / empty → sender.
    Otherwise exact/case-insensitive name match in org.
    Falls back to (None, raw owner_str) if no match found.
    """
    if owner_str.strip().lower() in ("yo", "me encargo", "me", ""):
        return sender.id, sender.display_name

    result = (
        db.table("people")
        .select("id, display_name")
        .eq("organization_id", org_id)
        .ilike("display_name", owner_str.strip())
        .limit(1)
        .execute()
    )
    if result.data:
        row = result.data[0]
        return row["id"], row["display_name"]

    return None, owner_str.strip()


def _build_task_data(
    extracted: ExtractedTask,
    org: Org,
    project_id: Optional[str],
    is_global: bool,
    owner_id: Optional[str],
    owner_name: str,
    inbound_id: Optional[str],
    source_text: str,
) -> dict[str, Any]:
    """Build the `tasks` row. The idempotency_key is added at insert time."""
    return {
        "organization_id": org.id,
        "project_id": project_id,
        "is_global": is_global,
        "owner_id": owner_id,
        "owner_name": owner_name,
        "task_title": extracted.task_title,
        "description": extracted.description,
        "due_date": extracted.due_date,
        "status": extracted.status,
        "priority": extracted.priority,
        "source_message_id": inbound_id,
        "source_type": "whatsapp",
        "source_text": source_text,
        "confidence": extracted.confidence,
        "extraction_payload": extracted.model_dump(mode="json"),
    }


def _stage_confirmation(
    db,
    org: Org,
    person: Person,
    sender_phone: str,
    inbound_id: Optional[str],
    task_data: dict[str, Any],
    title: str,
    due_date: Optional[str],
    reply_to: str,
) -> None:
    """Stage a resolved task in a draft and ask the sender to confirm.

    The task is NOT written to `tasks` yet — that happens in
    _handle_confirmation_reply once the sender replies "si".
    """
    draft_data = {
        "organization_id": org.id,
        "source_message_id": inbound_id,
        "sender_phone": sender_phone,
        "people_id": person.id,
        "extraction_payload": task_data["extraction_payload"],
        "resolved_task": task_data,
        "status": "awaiting_confirmation",
    }
    try:
        db.table("task_drafts").insert(draft_data).execute()
    except Exception:
        # task_drafts_one_pending constraint: a conversation is already open.
        log.warning("Confirmation draft conflict for sender=%s org=%s", sender_phone, org.id)
        send_whatsapp(
            reply_to,
            "Tenés una tarea pendiente de confirmar. Respondé *si* o *no* primero.",
        )
        return

    due_suffix = f" — {due_date}" if due_date else ""
    send_whatsapp(reply_to, f"Registré: {title}{due_suffix}. ¿Confirmás? (si/no)")


def _insert_task_immediate(
    db,
    extracted: ExtractedTask,
    org: Org,
    project_id: Optional[str],
    is_global: bool,
    owner_id: Optional[str],
    owner_name: str,
    inbound_id: Optional[str],
    source_text: str,
    reply_to: str,
) -> None:
    """Write the task row immediately (pre-confirmation-gate behavior)."""
    idempotency_key = f"task:msg:{inbound_id}" if inbound_id else None
    task_data: dict[str, Any] = {
        "organization_id": org.id,
        "project_id": project_id,
        "is_global": is_global,
        "owner_id": owner_id,
        "owner_name": owner_name,
        "task_title": extracted.task_title,
        "description": extracted.description,
        "due_date": extracted.due_date,
        "status": extracted.status,
        "priority": extracted.priority,
        "source_message_id": inbound_id,
        "source_type": "whatsapp",
        "source_text": source_text,
        "confidence": extracted.confidence,
        "extraction_payload": extracted.model_dump(mode="json"),
        "idempotency_key": idempotency_key,
    }

    try:
        db.table("tasks").insert(task_data).execute()
    except Exception:
        log.exception("Failed to insert task for org=%s", org.id)
        send_whatsapp(reply_to, "Hubo un error registrando la tarea. Por favor intentá de nuevo.")
        return

    due_suffix = f" — {extracted.due_date}" if extracted.due_date else ""
    send_whatsapp(reply_to, f"Registré: {extracted.task_title}{due_suffix}. ¿Confirmás?")


def _insert_task(
    db,
    extracted: ExtractedTask,
    org: Org,
    project_id: Optional[str],
    is_global: bool,
    owner_id: Optional[str],
    owner_name: str,
    inbound_id: Optional[str],
    source_text: str,
    reply_to: str,
    person: Person,
    sender_phone: str,
    confirmation: bool = True,
) -> None:
    if not confirmation:
        _insert_task_immediate(
            db=db,
            extracted=extracted,
            org=org,
            project_id=project_id,
            is_global=is_global,
            owner_id=owner_id,
            owner_name=owner_name,
            inbound_id=inbound_id,
            source_text=source_text,
            reply_to=reply_to,
        )
        return

    task_data = _build_task_data(
        extracted=extracted,
        org=org,
        project_id=project_id,
        is_global=is_global,
        owner_id=owner_id,
        owner_name=owner_name,
        inbound_id=inbound_id,
        source_text=source_text,
    )
    _stage_confirmation(
        db=db,
        org=org,
        person=person,
        sender_phone=sender_phone,
        inbound_id=inbound_id,
        task_data=task_data,
        title=extracted.task_title,
        due_date=extracted.due_date,
        reply_to=reply_to,
    )


def _handle_global(
    db,
    extracted: ExtractedTask,
    org: Org,
    person: Person,
    owner_id: Optional[str],
    owner_name: str,
    inbound_id: Optional[str],
    body: str,
    reply_to: str,
    sender_phone: str,
    confirmation: bool = True,
) -> None:
    if not _can_create_global(db, org.id, person):
        send_whatsapp(
            reply_to,
            "No tenés permiso para crear tareas globales. Contactá a la directora.",
        )
        return
    _insert_task(
        db=db,
        extracted=extracted,
        org=org,
        project_id=None,
        is_global=True,
        owner_id=owner_id,
        owner_name=owner_name,
        inbound_id=inbound_id,
        source_text=body,
        reply_to=reply_to,
        person=person,
        sender_phone=sender_phone,
        confirmation=confirmation,
    )


def _insert_draft_and_ask(
    db,
    extracted: ExtractedTask,
    org: Org,
    person: Person,
    sender_phone: str,
    inbound_id: Optional[str],
    active_projects: list[dict[str, Any]],
    reply_to: str,
) -> None:
    offered_projects = [
        {"id": p["id"], "name": p["name"], "slug": p["slug"]}
        for p in active_projects
    ]

    draft_data = {
        "organization_id": org.id,
        "source_message_id": inbound_id,
        "sender_phone": sender_phone,
        "people_id": person.id,
        "extraction_payload": extracted.model_dump(mode="json"),
        "offered_projects": offered_projects,
        "status": "awaiting_project_choice",
    }

    try:
        db.table("task_drafts").insert(draft_data).execute()
    except Exception:
        # task_drafts_one_pending constraint: a draft already exists for this sender.
        log.warning("Draft insert conflict for sender=%s org=%s — keeping existing", sender_phone, org.id)
        send_whatsapp(
            reply_to,
            "Tenés una tarea pendiente de clasificar. Respondé primero con el número o nombre del proyecto.",
        )
        return

    project_lines = "\n".join(
        f"{i + 1} — {p['name']}" for i, p in enumerate(offered_projects)
    )
    menu = (
        f"Registré: {extracted.task_title}.\n\n"
        "¿Dónde la ubicamos?\n"
        "0 — Tarea individual (sin proyecto)\n"
        "G — Tarea global (toda la organización)\n"
        f"{project_lines}\n\n"
        "Respondé con 0, G, el número o el nombre del proyecto."
    )
    send_whatsapp(reply_to, menu)


def _handle_draft_reply(
    db,
    draft_row: dict,
    reply_text: str,
    org: Org,
    person: Person,
    sender_phone: str,
    reply_to: str,
    confirmation: bool = True,
) -> None:
    """Parse the reply to a disambiguation menu and stage or insert the task."""
    draft_id = draft_row["id"]
    offered_projects: list[dict] = draft_row["offered_projects"] or []
    extraction_payload: dict = draft_row["extraction_payload"]

    text = reply_text.strip()
    text_upper = text.upper()

    project_id: Optional[str] = None
    is_global = False

    if text_upper == "0":
        # standalone
        pass
    elif text_upper == "G":
        is_global = True
        if not _can_create_global(db, org.id, person):
            send_whatsapp(
                reply_to,
                "No tenés permiso para crear tareas globales. Contactá a la directora.",
            )
            return
    else:
        matched_project = _parse_project_choice(text, offered_projects)
        if matched_project is None:
            project_lines = "\n".join(
                f"{i + 1} — {p['name']}" for i, p in enumerate(offered_projects)
            )
            send_whatsapp(
                reply_to,
                "No entendí la respuesta. ¿Dónde ubicamos la tarea?\n"
                "0 — Tarea individual (sin proyecto)\n"
                "G — Tarea global (toda la organización)\n"
                f"{project_lines}\n\n"
                "Respondé con 0, G, el número o el nombre del proyecto.",
            )
            return
        project_id = matched_project["id"]

    extracted = ExtractedTask.model_validate(extraction_payload)
    owner_id, owner_name = _map_owner(db, extracted.owner, org.id, person)

    # Retrieve original body for source_text
    source_text = ""
    if draft_row.get("source_message_id"):
        inb = (
            db.table("inbound_messages")
            .select("body")
            .eq("id", draft_row["source_message_id"])
            .limit(1)
            .execute()
        )
        if inb.data:
            source_text = inb.data[0].get("body") or ""

    if not confirmation:
        idempotency_key = f"task:draft:{draft_id}"
        task_data: dict[str, Any] = {
            "organization_id": org.id,
            "project_id": project_id,
            "is_global": is_global,
            "owner_id": owner_id,
            "owner_name": owner_name,
            "task_title": extracted.task_title,
            "description": extracted.description,
            "due_date": extracted.due_date,
            "status": extracted.status,
            "priority": extracted.priority,
            "source_message_id": draft_row.get("source_message_id"),
            "source_type": "whatsapp",
            "source_text": source_text,
            "confidence": extracted.confidence,
            "extraction_payload": extraction_payload,
            "idempotency_key": idempotency_key,
        }

        try:
            task_result = db.table("tasks").insert(task_data).execute()
            task_id = task_result.data[0]["id"]
        except Exception:
            log.exception("Failed to insert task from draft=%s", draft_id)
            send_whatsapp(reply_to, "Hubo un error creando la tarea. Por favor intentá de nuevo.")
            return

        db.table("task_drafts").update(
            {"status": "confirmed", "resolved_task_id": task_id}
        ).eq("id", draft_id).execute()

        due_suffix = f" — {extracted.due_date}" if extracted.due_date else ""
        send_whatsapp(reply_to, f"Registré: {extracted.task_title}{due_suffix}. ¿Confirmás?")
        return

    task_data = _build_task_data(
        extracted=extracted,
        org=org,
        project_id=project_id,
        is_global=is_global,
        owner_id=owner_id,
        owner_name=owner_name,
        inbound_id=draft_row.get("source_message_id"),
        source_text=source_text,
    )

    # Transition this same draft from project-choice → confirmation. The task is
    # written to `tasks` only once the sender replies "si" (_handle_confirmation_reply).
    try:
        db.table("task_drafts").update(
            {"status": "awaiting_confirmation", "resolved_task": task_data}
        ).eq("id", draft_id).execute()
    except Exception:
        log.exception("Failed to stage confirmation for draft=%s", draft_id)
        send_whatsapp(reply_to, "Hubo un error procesando la tarea. Por favor intentá de nuevo.")
        return

    due_suffix = f" — {extracted.due_date}" if extracted.due_date else ""
    send_whatsapp(reply_to, f"Registré: {extracted.task_title}{due_suffix}. ¿Confirmás? (si/no)")


_AFFIRM = {
    "si", "sii", "siii", "sip", "sisi", "dale", "ok", "oka", "okok",
    "okay", "okey", "oki", "listo", "va", "vale", "bien", "confirmo",
    "confirmado", "confirmar", "correcto", "exacto", "perfecto", "claro",
    "obvio", "yes", "👍", "👍🏻", "👍🏼", "👍🏽", "👍🏾", "👍🏿", "✅",
}
# Negation words. Checked against ANY token (so "mejor no" cancels too), so this
# set must stay strict — only words that unambiguously mean "no".
_NEGATE = {
    "no", "nop", "nope", "noo", "cancelar", "cancela", "cancelo",
    "negativo", "descartar", "descarta", "anular", "anula", "❌",
}


def _classify_confirmation(text: str) -> str:
    """Classify a confirmation reply as 'yes', 'no', or 'unknown'.

    Negation dominates: any negation token anywhere means "no" (handles "mejor no").
    Affirmation is matched only on the whole reply or its first word to avoid false
    positives from longer sentences.
    """
    # Strip accents so "sí" == "si", lowercase, drop surrounding punctuation.
    decomposed = unicodedata.normalize("NFKD", text)
    norm = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    stripped = norm.strip(" \t\n.!¡¿?,;:")
    words = [w.strip(".!¡¿?,;:") for w in stripped.split()]

    if any(w in _NEGATE for w in words):
        return "no"
    if "cancel" in stripped or "descart" in stripped or "anul" in stripped:
        return "no"
    if stripped in _AFFIRM or (words and words[0] in _AFFIRM):
        return "yes"
    if "confirm" in stripped:
        return "yes"
    return "unknown"


def _handle_confirmation_reply(
    db,
    draft_row: dict,
    reply_text: str,
    reply_to: str,
) -> None:
    """Resolve a si/no reply to a staged task: 'si' writes it, 'no' cancels it."""
    draft_id = draft_row["id"]
    decision = _classify_confirmation(reply_text)

    if decision == "no":
        db.table("task_drafts").update({"status": "cancelled"}).eq("id", draft_id).execute()
        send_whatsapp(reply_to, "Cancelado. No registré la tarea.")
        return

    if decision == "unknown":
        send_whatsapp(
            reply_to,
            "¿Confirmás la tarea? Respondé *si* para registrarla o *no* para cancelarla.",
        )
        return

    # decision == "yes" → write the staged task to `tasks` now.
    task_data = dict(draft_row.get("resolved_task") or {})
    if not task_data:
        log.error("Confirmation for draft=%s has no resolved_task payload", draft_id)
        db.table("task_drafts").update({"status": "cancelled"}).eq("id", draft_id).execute()
        send_whatsapp(reply_to, "No pude recuperar la tarea. Por favor enviala de nuevo.")
        return

    task_data["idempotency_key"] = f"task:draft:{draft_id}"
    try:
        result = db.table("tasks").insert(task_data).execute()
        task_id = result.data[0]["id"]
    except Exception:
        log.exception("Failed to insert confirmed task from draft=%s", draft_id)
        send_whatsapp(reply_to, "Hubo un error registrando la tarea. Por favor intentá de nuevo.")
        return

    db.table("task_drafts").update(
        {"status": "confirmed", "resolved_task_id": task_id}
    ).eq("id", draft_id).execute()

    title = task_data.get("task_title", "la tarea")
    due = task_data.get("due_date")
    due_suffix = f" — {due}" if due else ""
    send_whatsapp(reply_to, f"Listo ✅ {title}{due_suffix} quedó registrada.")


def _parse_project_choice(
    text: str, offered_projects: list[dict]
) -> Optional[dict]:
    """Return the matched project dict from offered_projects, or None."""
    # Numeric choice (1-based)
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(offered_projects):
            return offered_projects[idx]

    # Name substring match (case-insensitive)
    lower = text.lower()
    for project in offered_projects:
        if lower in project["name"].lower() or project["name"].lower() in lower:
            return project

    return None
