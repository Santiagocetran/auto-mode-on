"""Tests for app.services.resolution."""

from unittest.mock import patch

from tests.conftest import make_query_mock

from app.services.resolution import (
    Org,
    Person,
    normalize_twilio_whatsapp,
    resolve_org,
    resolve_sender,
    strip_whatsapp_prefix,
)


# ---------------------------------------------------------------------------
# Phone helpers — pure functions, no mocking needed
# ---------------------------------------------------------------------------


def test_normalize_twilio_whatsapp_adds_prefix():
    assert normalize_twilio_whatsapp("+14155238886") == "whatsapp:+14155238886"


def test_normalize_twilio_whatsapp_idempotent():
    assert normalize_twilio_whatsapp("whatsapp:+14155238886") == "whatsapp:+14155238886"


def test_strip_whatsapp_prefix_removes_prefix():
    assert strip_whatsapp_prefix("whatsapp:+5491112345678") == "+5491112345678"


def test_strip_whatsapp_prefix_no_op_when_already_stripped():
    assert strip_whatsapp_prefix("+5491112345678") == "+5491112345678"


# ---------------------------------------------------------------------------
# resolve_org
# ---------------------------------------------------------------------------


def test_resolve_org_found():
    channel_row = {
        "id": "channel-id-1",
        "organization_id": "org-id-1",
        "organizations": {"id": "org-id-1", "name": "Fundación Esperanza"},
    }
    mock_q = make_query_mock(data=[channel_row])

    with patch("app.services.resolution.get_db") as mock_get_db:
        mock_get_db.return_value.table.return_value = mock_q
        org = resolve_org("whatsapp:+14155238886")

    assert org is not None
    assert isinstance(org, Org)
    assert org.id == "org-id-1"
    assert org.name == "Fundación Esperanza"
    assert org.channel_id == "channel-id-1"


def test_resolve_org_not_found():
    mock_q = make_query_mock(data=[])

    with patch("app.services.resolution.get_db") as mock_get_db:
        mock_get_db.return_value.table.return_value = mock_q
        org = resolve_org("whatsapp:+19999999999")

    assert org is None


def test_resolve_org_normalizes_prefix():
    """resolve_org must add the whatsapp: prefix before querying."""
    channel_row = {
        "id": "chan-1",
        "organization_id": "org-1",
        "organizations": {"id": "org-1", "name": "Test Org"},
    }
    mock_q = make_query_mock(data=[channel_row])

    with patch("app.services.resolution.get_db") as mock_get_db:
        mock_get_db.return_value.table.return_value = mock_q
        org = resolve_org("+14155238886")  # no prefix supplied

    assert org is not None
    # The eq filter was called with the normalized form
    mock_q.eq.assert_any_call("whatsapp_number", "whatsapp:+14155238886")


# ---------------------------------------------------------------------------
# resolve_sender
# ---------------------------------------------------------------------------


def test_resolve_sender_found():
    people_row = {
        "id": "person-id-1",
        "display_name": "Mateo",
        "whatsapp_number": "+5491112345678",
        "user_id": "user-id-1",
    }
    mock_q = make_query_mock(data=[people_row])

    with patch("app.services.resolution.get_db") as mock_get_db:
        mock_get_db.return_value.table.return_value = mock_q
        person = resolve_sender("org-id-1", "whatsapp:+5491112345678")

    assert person is not None
    assert isinstance(person, Person)
    assert person.id == "person-id-1"
    assert person.display_name == "Mateo"
    assert person.user_id == "user-id-1"


def test_resolve_sender_strips_prefix():
    """resolve_sender must strip whatsapp: before matching people.whatsapp_number."""
    people_row = {
        "id": "person-id-1",
        "display_name": "Mateo",
        "whatsapp_number": "+5491112345678",
        "user_id": None,
    }
    mock_q = make_query_mock(data=[people_row])

    with patch("app.services.resolution.get_db") as mock_get_db:
        mock_get_db.return_value.table.return_value = mock_q
        resolve_sender("org-id-1", "whatsapp:+5491112345678")

    # The eq filter for phone must have stripped the prefix
    mock_q.eq.assert_any_call("whatsapp_number", "+5491112345678")


def test_resolve_sender_not_found():
    mock_q = make_query_mock(data=[])

    with patch("app.services.resolution.get_db") as mock_get_db:
        mock_get_db.return_value.table.return_value = mock_q
        person = resolve_sender("org-id-1", "whatsapp:+5499999999")

    assert person is None


def test_resolve_sender_multi_org_scoped_by_org_id():
    """Mateo's phone exists in two orgs. resolve_sender scopes by org_id so the
    correct record is returned based on which org channel was used (To)."""
    # Simulate the DB returning Mateo for Fundación Esperanza specifically
    people_row_esperanza = {
        "id": "mateo-esperanza-id",
        "display_name": "Mateo",
        "whatsapp_number": "+5491112345678",
        "user_id": "user-mateo",
    }
    mock_q = make_query_mock(data=[people_row_esperanza])

    with patch("app.services.resolution.get_db") as mock_get_db:
        mock_get_db.return_value.table.return_value = mock_q
        person = resolve_sender("11111111-1111-1111-1111-111111111111", "whatsapp:+5491112345678")

    assert person is not None
    assert person.id == "mateo-esperanza-id"
    # org scoping was applied
    mock_q.eq.assert_any_call("organization_id", "11111111-1111-1111-1111-111111111111")
