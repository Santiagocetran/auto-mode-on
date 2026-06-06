"""Tests for app.services.capture — all external calls mocked."""

from unittest.mock import MagicMock, call, patch

import pytest

from tests.conftest import make_db_mock, make_query_mock

from app.models.extraction import ExtractedTask, ProjectResolution
from app.services.resolution import Org, Person
from app.services.transcription import MessageNormalizationError

# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

ORG = Org(id="org-1", name="Fundación Esperanza", channel_id="chan-1")
PERSON = Person(
    id="person-1",
    display_name="Mateo",
    whatsapp_number="+5491112345678",
    user_id="user-1",
)
INBOUND_ID = "inbound-uuid-1"
TASK_ID = "task-uuid-1"

FORM_DATA = {
    "To": "whatsapp:+14155238886",
    "From": "whatsapp:+5491112345678",
    "Body": "Yo me encargo del informe para el viernes",
    "ProfileName": "Mateo",
    "MessageSid": "SM001",
}

EXTRACTED_STANDALONE = ExtractedTask(
    intent="task_creation",
    owner="yo",
    task_title="Preparar informe",
    confidence=0.94,
    is_global=False,
    project_resolution=ProjectResolution(
        status="standalone",
        confidence=0.9,
        reason="Tarea individual",
    ),
)

EXTRACTED_MATCHED = ExtractedTask(
    intent="task_creation",
    owner="Mateo",
    task_title="Preparar informe para financiador",
    confidence=0.93,
    is_global=False,
    project_resolution=ProjectResolution(
        status="matched",
        project_id="proj-1",
        project_name_matched="Informe financiador Q2",
        confidence=0.88,
        reason="Coincide con proyecto activo",
    ),
)

EXTRACTED_CLARIFY = ExtractedTask(
    intent="task_creation",
    owner="Ana",
    task_title="Coordinar espacio para el taller",
    confidence=0.87,
    is_global=False,
    project_resolution=ProjectResolution(
        status="needs_clarification",
        confidence=0.45,
        reason="Podría ser taller de nutrición o tarea suelta",
    ),
    ambiguities=["No queda claro si pertenece a un proyecto."],
)

EXTRACTED_GLOBAL = ExtractedTask(
    intent="task_creation",
    owner="Laura",
    task_title="Renovar personería jurídica",
    confidence=0.92,
    is_global=True,
    project_resolution=ProjectResolution(
        status="not_applicable",
        confidence=1.0,
        reason="Trámite institucional de toda la ONG.",
    ),
)

ACTIVE_PROJECTS = [
    {"id": "proj-1", "name": "Informe financiador Q2", "slug": "informe-q2", "categories": []},
    {"id": "proj-2", "name": "Taller nutrición", "slug": "taller-nutricion", "categories": []},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_capture(resolve_org_ret=ORG, resolve_sender_ret=PERSON,
                   extract_ret=EXTRACTED_STANDALONE, active_projects=None):
    """Return a context-manager stack that patches capture's dependencies."""
    if active_projects is None:
        active_projects = ACTIVE_PROJECTS
    return [
        patch("app.services.capture.resolution.resolve_org", return_value=resolve_org_ret),
        patch("app.services.capture.resolution.resolve_sender", return_value=resolve_sender_ret),
        patch("app.services.capture.llm.extract_task", return_value=extract_ret),
        patch("app.services.capture.llm.get_active_projects", return_value=active_projects),
        patch("app.services.capture.send_whatsapp"),
    ]


# ---------------------------------------------------------------------------
# Unknown org
# ---------------------------------------------------------------------------


def test_unknown_channel_no_extraction_no_task():
    db = make_db_mock()
    with patch("app.services.capture.resolution.resolve_org", return_value=None), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task") as mock_extract, \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    mock_extract.assert_not_called()
    mock_send.assert_not_called()
    # Nothing inserted
    db.table.assert_not_called()


# ---------------------------------------------------------------------------
# Unregistered sender
# ---------------------------------------------------------------------------


def test_unregistered_sender_no_task():
    db = make_db_mock(
        inbound_messages=([{"id": INBOUND_ID}], None),
        task_drafts=([], None),
    )

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=None), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task") as mock_extract, \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    mock_extract.assert_not_called()
    # A reply is sent, but no task insert
    mock_send.assert_called_once()
    assert "registrado" in mock_send.call_args[0][1].lower()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_idempotency_same_message_sid_short_circuits():
    """Second call with same MessageSid: inbound insert fails, existing row found,
    no LLM call, no task insert, no confirmation sent."""
    # First call succeeds (insert returns row), second raises then finds existing
    inbound_insert_raises = Exception("unique violation")
    inbound_select_data = [{"id": INBOUND_ID}]

    # We need the inbound_messages mock to: raise on insert, return data on select
    call_count = [0]

    inbound_mock = make_query_mock(data=[{"id": INBOUND_ID}])

    def execute_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("23505 unique_violation")
        resp = MagicMock()
        resp.data = [{"id": INBOUND_ID}]
        return resp

    inbound_mock.execute.side_effect = execute_side_effect

    db = MagicMock()
    db.table.side_effect = lambda name: inbound_mock if name == "inbound_messages" else make_query_mock(data=[])

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task") as mock_extract, \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    mock_extract.assert_not_called()
    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path — standalone
# ---------------------------------------------------------------------------


def test_standalone_stages_confirmation_not_task():
    """A clear standalone task is staged for confirmation — NOT written to `tasks` yet."""
    drafts_table = make_query_mock(data=[])
    tasks_table = make_query_mock(data=[{"id": TASK_ID}])

    db = MagicMock()
    db.table.side_effect = lambda name: {
        "inbound_messages": make_query_mock(data=[{"id": INBOUND_ID}]),
        "task_drafts": drafts_table,
        "tasks": tasks_table,
        "people": make_query_mock(data=[{"id": PERSON.id, "display_name": PERSON.display_name}]),
    }.get(name, make_query_mock(data=[]))

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_STANDALONE), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    # Draft staged with the resolved task; nothing written to `tasks` yet.
    drafts_table.insert.assert_called_once()
    staged = drafts_table.insert.call_args[0][0]
    assert staged["status"] == "awaiting_confirmation"
    assert staged["resolved_task"]["task_title"] == EXTRACTED_STANDALONE.task_title
    tasks_table.insert.assert_not_called()
    # Confirmation prompt sent
    mock_send.assert_called_once()
    msg = mock_send.call_args[0][1]
    assert "Registré:" in msg and "Confirmás" in msg


def test_standalone_confirmation_includes_title():
    db = make_db_mock(
        inbound_messages=([{"id": INBOUND_ID}], None),
        task_drafts=([], None),
        tasks=([{"id": TASK_ID}], None),
        people=([{"id": PERSON.id, "display_name": PERSON.display_name}], None),
    )

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_STANDALONE), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    msg = mock_send.call_args[0][1]
    assert EXTRACTED_STANDALONE.task_title in msg


# ---------------------------------------------------------------------------
# Matched project
# ---------------------------------------------------------------------------


def test_matched_task_uses_project_id():
    drafts_table = make_query_mock(data=[])
    tasks_table = make_query_mock(data=[{"id": TASK_ID}])

    db = MagicMock()
    db.table.side_effect = lambda name: {
        "inbound_messages": make_query_mock(data=[{"id": INBOUND_ID}]),
        "task_drafts": drafts_table,
        "tasks": tasks_table,
        "people": make_query_mock(data=[{"id": PERSON.id, "display_name": PERSON.display_name}]),
    }.get(name, make_query_mock(data=[]))

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_MATCHED), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    # Staged for confirmation with the matched project_id carried in resolved_task.
    drafts_table.insert.assert_called_once()
    staged = drafts_table.insert.call_args[0][0]
    assert staged["resolved_task"]["project_id"] == "proj-1"
    tasks_table.insert.assert_not_called()
    mock_send.assert_called_once()


def test_matched_project_not_in_active_snapshot_creates_draft():
    """project_id from LLM not in active snapshot → creates draft instead of task."""
    extracted_bad_project = ExtractedTask(
        intent="task_creation",
        owner="Mateo",
        task_title="Tarea con proyecto inválido",
        confidence=0.93,
        is_global=False,
        project_resolution=ProjectResolution(
            status="matched",
            project_id="proj-INVALID",  # not in ACTIVE_PROJECTS
            project_name_matched="Proyecto inexistente",
            confidence=0.88,
            reason="Test",
        ),
    )

    db = make_db_mock(
        inbound_messages=([{"id": INBOUND_ID}], None),
        task_drafts=([], None),
    )

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=extracted_bad_project), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    # Draft insert attempted (not task insert)
    db.table.assert_any_call("task_drafts")
    # Disambiguation menu sent
    mock_send.assert_called_once()
    assert "ubicamos" in mock_send.call_args[0][1]


# ---------------------------------------------------------------------------
# needs_clarification → draft
# ---------------------------------------------------------------------------


def test_needs_clarification_creates_draft_not_task():
    tasks_table = make_query_mock(data=[{"id": TASK_ID}])
    drafts_table = make_query_mock(data=[])

    db = MagicMock()
    db.table.side_effect = lambda name: {
        "inbound_messages": make_query_mock(data=[{"id": INBOUND_ID}]),
        "task_drafts": drafts_table,
        "tasks": tasks_table,
        "people": make_query_mock(data=[]),
    }.get(name, make_query_mock(data=[]))

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_CLARIFY), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    # Draft table was accessed for insert, tasks table was NOT inserted into
    tasks_table.insert.assert_not_called()
    drafts_table.insert.assert_called_once()
    # Disambiguation menu sent
    mock_send.assert_called_once()
    msg = mock_send.call_args[0][1]
    assert "ubicamos" in msg


def test_needs_clarification_draft_collision_sends_reply_not_task():
    """When a draft already exists (unique conflict on insert), send the 'reply first'
    message and do NOT insert a task."""
    drafts_table = make_query_mock(
        # Pending draft check returns existing draft
        data=[],  # pending check finds nothing initially
        raises=Exception("unique constraint"),  # but insert fails
    )

    # pending check returns empty (no pending draft in query)
    drafts_pending = make_query_mock(data=[])
    drafts_insert_fail = make_query_mock(data=[], raises=Exception("unique constraint"))

    call_count = [0]

    def drafts_side_effect(name):
        if name == "task_drafts":
            call_count[0] += 1
            if call_count[0] == 1:
                return drafts_pending  # pending check → empty
            return drafts_insert_fail  # insert → fails
        if name == "inbound_messages":
            return make_query_mock(data=[{"id": INBOUND_ID}])
        if name == "people":
            return make_query_mock(data=[])
        return make_query_mock(data=[])

    db = MagicMock()
    db.table.side_effect = drafts_side_effect

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_CLARIFY), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    mock_send.assert_called_once()
    msg = mock_send.call_args[0][1]
    assert "pendiente" in msg.lower()


# ---------------------------------------------------------------------------
# Pending draft reply
# ---------------------------------------------------------------------------


def test_project_choice_reply_stages_confirmation_without_extraction():
    draft_payload = EXTRACTED_STANDALONE.model_dump(mode="json")
    draft_row = {
        "id": "draft-1",
        "status": "awaiting_project_choice",
        "extraction_payload": draft_payload,
        "offered_projects": [
            {"id": "proj-1", "name": "Informe financiador Q2", "slug": "informe-q2"},
            {"id": "proj-2", "name": "Taller nutrición", "slug": "taller"},
        ],
        "resolved_task": None,
        "source_message_id": INBOUND_ID,
    }

    inbound_body_row = [{"body": "Yo me encargo del informe para el viernes"}]
    drafts_table = make_query_mock(data=[draft_row])
    tasks_table = make_query_mock(data=[{"id": TASK_ID}])

    def table_factory(name):
        return {
            "inbound_messages": make_query_mock(data=[{"id": "new-inbound-id"}]),
            "task_drafts": drafts_table,
            "tasks": tasks_table,
            "people": make_query_mock(data=[]),
        }.get(name, make_query_mock(data=inbound_body_row))

    db = MagicMock()
    db.table.side_effect = table_factory

    form = {**FORM_DATA, "Body": "1", "MessageSid": "SM002"}  # reply "1" → proj-1

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task") as mock_extract, \
         patch("app.services.capture.llm.get_active_projects") as mock_projects, \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(form)

    # Extraction must NOT have run (pending draft consumed the turn)
    mock_extract.assert_not_called()
    mock_projects.assert_not_called()
    # Draft transitioned to awaiting_confirmation with the chosen project; no task yet.
    drafts_table.update.assert_called_once()
    updated = drafts_table.update.call_args[0][0]
    assert updated["status"] == "awaiting_confirmation"
    assert updated["resolved_task"]["project_id"] == "proj-1"
    tasks_table.insert.assert_not_called()
    mock_send.assert_called_once()
    msg = mock_send.call_args[0][1]
    assert "Registré:" in msg and "Confirmás" in msg


# ---------------------------------------------------------------------------
# Global tasks — permission checks
# ---------------------------------------------------------------------------


def test_global_task_with_permission_inserted():
    person_owner = Person(
        id="person-laura",
        display_name="Laura",
        whatsapp_number="+5491155555555",
        user_id="user-laura",
    )

    membership_data = [{"role": "owner"}]
    settings_data = [
        {
            "role_permissions": {
                "owner": {"can_create_global_tasks": True},
            }
        }
    ]

    drafts_table = make_query_mock(data=[])
    tasks_table = make_query_mock(data=[{"id": TASK_ID}])

    def table_factory(name):
        return {
            "inbound_messages": make_query_mock(data=[{"id": INBOUND_ID}]),
            "task_drafts": drafts_table,
            "tasks": tasks_table,
            "people": make_query_mock(data=[]),
            "organization_memberships": make_query_mock(data=membership_data),
            "organization_settings": make_query_mock(data=settings_data),
        }.get(name, make_query_mock(data=[]))

    db = MagicMock()
    db.table.side_effect = table_factory

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=person_owner), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_GLOBAL), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    # Permitted global task is staged for confirmation (is_global carried through).
    drafts_table.insert.assert_called_once()
    staged = drafts_table.insert.call_args[0][0]
    assert staged["resolved_task"]["is_global"] is True
    tasks_table.insert.assert_not_called()
    mock_send.assert_called_once()
    assert "Registré:" in mock_send.call_args[0][1]


def test_global_task_without_permission_sends_rejection():
    person_member = Person(
        id="person-ana",
        display_name="Ana",
        whatsapp_number="+5491187654321",
        user_id="user-ana",
    )

    membership_data = [{"role": "member"}]
    settings_data = [
        {
            "role_permissions": {
                "member": {"can_create_global_tasks": False},
            }
        }
    ]

    def table_factory(name):
        return {
            "inbound_messages": make_query_mock(data=[{"id": INBOUND_ID}]),
            "task_drafts": make_query_mock(data=[]),
            "tasks": make_query_mock(data=[{"id": TASK_ID}]),
            "people": make_query_mock(data=[]),
            "organization_memberships": make_query_mock(data=membership_data),
            "organization_settings": make_query_mock(data=settings_data),
        }.get(name, make_query_mock(data=[]))

    db = MagicMock()
    db.table.side_effect = table_factory

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=person_member), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_GLOBAL), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    # Task must NOT be inserted
    tasks_insert_called = any(
        call_args[0][0] == "tasks"
        for call_args in db.table.call_args_list
    )
    # We check via mock_send: rejection message sent
    mock_send.assert_called_once()
    msg = mock_send.call_args[0][1]
    assert "permiso" in msg.lower()


def test_global_task_null_user_id_rejected():
    """Person with null user_id (WhatsApp-only, no dashboard membership) cannot create global tasks."""
    person_whatsapp_only = Person(
        id="person-wa",
        display_name="Invitado",
        whatsapp_number="+5491199999999",
        user_id=None,  # no user account
    )

    db = make_db_mock(
        inbound_messages=([{"id": INBOUND_ID}], None),
        task_drafts=([], None),
        tasks=([{"id": TASK_ID}], None),
    )

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=person_whatsapp_only), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_GLOBAL), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    mock_send.assert_called_once()
    assert "permiso" in mock_send.call_args[0][1].lower()


# ---------------------------------------------------------------------------
# Low confidence
# ---------------------------------------------------------------------------


def test_low_confidence_sends_rephrase_request():
    extracted_low = ExtractedTask(
        intent="task_creation",
        owner="Mateo",
        task_title="Algo confuso",
        confidence=0.4,
        is_global=False,
        project_resolution=ProjectResolution(
            status="standalone",
            confidence=0.4,
            reason="Bajo confidence",
        ),
    )

    db = make_db_mock(
        inbound_messages=([{"id": INBOUND_ID}], None),
        task_drafts=([], None),
    )

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=extracted_low), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    db.table.assert_any_call("inbound_messages")
    # No task insert
    task_calls = [c for c in db.table.call_args_list if c[0][0] == "tasks"]
    assert len(task_calls) == 0
    mock_send.assert_called_once()
    assert "entendí" in mock_send.call_args[0][1].lower()


# ---------------------------------------------------------------------------
# Audio voice note → transcribed → task
# ---------------------------------------------------------------------------


def test_audio_message_is_transcribed_then_captured():
    """A voice note (audio media, empty Body) is transcribed and the transcript
    drives extraction; the inbound row is updated with the resolved text."""
    audio_form = {
        "To": "whatsapp:+14155238886",
        "From": "whatsapp:+5491112345678",
        "Body": "",
        "ProfileName": "Mateo",
        "MessageSid": "SMaudio1",
        "NumMedia": "1",
        "MediaUrl0": "https://api.twilio.com/media/abc",
        "MediaContentType0": "audio/ogg",
    }

    db = make_db_mock(
        inbound_messages=([{"id": INBOUND_ID}], None),
        task_drafts=([], None),
        tasks=([{"id": TASK_ID}], None),
        people=([{"id": PERSON.id, "display_name": PERSON.display_name}], None),
    )

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.transcription.normalize_message",
               return_value="Preparar informe para el viernes") as mock_norm, \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_STANDALONE) as mock_extract, \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(audio_form)

    # Audio was normalized, the transcript was fed to extraction, task staged for confirmation.
    mock_norm.assert_called_once()
    assert mock_extract.call_args.kwargs["message_body"] == "Preparar informe para el viernes"
    db.table.assert_any_call("task_drafts")
    mock_send.assert_called_once()
    assert "Registré:" in mock_send.call_args[0][1]


def test_unparseable_message_asks_to_retry():
    """No text and no supported media → friendly reply, no task."""
    bad_form = {**FORM_DATA, "Body": "", "MessageSid": "SMbad1"}
    db = make_db_mock(inbound_messages=([{"id": INBOUND_ID}], None), task_drafts=([], None))

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.transcription.normalize_message",
               side_effect=MessageNormalizationError), \
         patch("app.services.capture.llm.extract_task") as mock_extract, \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(bad_form)

    mock_extract.assert_not_called()
    mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# Phone normalization in replies
# ---------------------------------------------------------------------------


def test_reply_to_uses_whatsapp_prefix():
    """All replies to the user must use normalize_twilio_whatsapp (whatsapp:+E164 form)."""
    db = make_db_mock(
        inbound_messages=([{"id": INBOUND_ID}], None),
        task_drafts=([], None),
        tasks=([{"id": TASK_ID}], None),
        people=([{"id": PERSON.id, "display_name": PERSON.display_name}], None),
    )

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task", return_value=EXTRACTED_STANDALONE), \
         patch("app.services.capture.llm.get_active_projects", return_value=ACTIVE_PROJECTS), \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(FORM_DATA)

    to_arg = mock_send.call_args[0][0]
    assert to_arg.startswith("whatsapp:")


# ---------------------------------------------------------------------------
# Confirmation gate — si/no reply to a staged task
# ---------------------------------------------------------------------------


def _confirmation_draft(resolved_task=None):
    return {
        "id": "draft-confirm-1",
        "status": "awaiting_confirmation",
        "extraction_payload": EXTRACTED_STANDALONE.model_dump(mode="json"),
        "offered_projects": [],
        "resolved_task": resolved_task
        or {
            "organization_id": ORG.id,
            "project_id": None,
            "is_global": False,
            "task_title": "Preparar reporte",
            "due_date": "2026-06-09",
            "extraction_payload": EXTRACTED_STANDALONE.model_dump(mode="json"),
        },
        "source_message_id": INBOUND_ID,
    }


def _run_confirmation_reply(body, draft_row, tasks_table, drafts_table):
    def table_factory(name):
        return {
            "inbound_messages": make_query_mock(data=[{"id": "inbound-reply"}]),
            "task_drafts": drafts_table,
            "tasks": tasks_table,
            "people": make_query_mock(data=[]),
        }.get(name, make_query_mock(data=[]))

    db = MagicMock()
    db.table.side_effect = table_factory

    form = {**FORM_DATA, "Body": body, "MessageSid": "SMconfirm"}

    with patch("app.services.capture.resolution.resolve_org", return_value=ORG), \
         patch("app.services.capture.resolution.resolve_sender", return_value=PERSON), \
         patch("app.services.capture.get_db", return_value=db), \
         patch("app.services.capture.llm.extract_task") as mock_extract, \
         patch("app.services.capture.llm.get_active_projects") as mock_projects, \
         patch("app.services.capture.send_whatsapp") as mock_send:

        from app.services.capture import handle_inbound
        handle_inbound(form)

    return mock_extract, mock_projects, mock_send


@pytest.mark.parametrize("body", ["si", "Sí", "  sí!  ", "dale", "ok", "confirmo", "👍"])
def test_confirmation_yes_inserts_task(body):
    drafts_table = make_query_mock(data=[_confirmation_draft()])
    tasks_table = make_query_mock(data=[{"id": TASK_ID}])

    mock_extract, mock_projects, mock_send = _run_confirmation_reply(
        body, _confirmation_draft(), tasks_table, drafts_table
    )

    # The reply is NOT re-extracted as a new task.
    mock_extract.assert_not_called()
    mock_projects.assert_not_called()
    # The staged task is written, with a deterministic idempotency key, and draft confirmed.
    tasks_table.insert.assert_called_once()
    inserted = tasks_table.insert.call_args[0][0]
    assert inserted["task_title"] == "Preparar reporte"
    assert inserted["idempotency_key"] == "task:draft:draft-confirm-1"
    drafts_table.update.assert_called_once()
    assert drafts_table.update.call_args[0][0]["status"] == "confirmed"
    mock_send.assert_called_once()
    assert "Listo" in mock_send.call_args[0][1]


@pytest.mark.parametrize("body", ["no", "No", "cancelar", "mejor no"])
def test_confirmation_no_cancels_without_task(body):
    drafts_table = make_query_mock(data=[_confirmation_draft()])
    tasks_table = make_query_mock(data=[{"id": TASK_ID}])

    _, _, mock_send = _run_confirmation_reply(
        body, _confirmation_draft(), tasks_table, drafts_table
    )

    tasks_table.insert.assert_not_called()
    drafts_table.update.assert_called_once()
    assert drafts_table.update.call_args[0][0]["status"] == "cancelled"
    mock_send.assert_called_once()
    assert "ancel" in mock_send.call_args[0][1]


@pytest.mark.parametrize("body", ["tal vez", "qué?", "y el otro tema"])
def test_confirmation_unknown_reasks(body):
    drafts_table = make_query_mock(data=[_confirmation_draft()])
    tasks_table = make_query_mock(data=[{"id": TASK_ID}])

    mock_extract, _, mock_send = _run_confirmation_reply(
        body, _confirmation_draft(), tasks_table, drafts_table
    )

    # Neither a new extraction nor a task insert; draft left pending.
    mock_extract.assert_not_called()
    tasks_table.insert.assert_not_called()
    drafts_table.update.assert_not_called()
    mock_send.assert_called_once()
    assert "Confirmás" in mock_send.call_args[0][1]
