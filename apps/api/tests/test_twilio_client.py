"""Tests for app.services.twilio_client."""

from unittest.mock import MagicMock, patch


def test_validate_signature_valid():
    """RequestValidator.validate returning True → our helper returns True."""
    with patch("app.services.twilio_client.get_settings") as mock_settings, \
         patch("app.services.twilio_client.RequestValidator") as mock_rv_cls:

        mock_settings.return_value.twilio_auth_token = "token"
        mock_settings.return_value.skip_twilio_signature_validation = False
        mock_rv_cls.return_value.validate.return_value = True

        from app.services.twilio_client import validate_signature
        result = validate_signature("https://example.com/whatsapp", {"Body": "hi"}, "sig")

    assert result is True
    mock_rv_cls.return_value.validate.assert_called_once_with(
        "https://example.com/whatsapp", {"Body": "hi"}, "sig"
    )


def test_validate_signature_invalid():
    """RequestValidator returning False → our helper returns False."""
    with patch("app.services.twilio_client.get_settings") as mock_settings, \
         patch("app.services.twilio_client.RequestValidator") as mock_rv_cls:

        mock_settings.return_value.twilio_auth_token = "token"
        mock_settings.return_value.skip_twilio_signature_validation = False
        mock_rv_cls.return_value.validate.return_value = False

        from app.services.twilio_client import validate_signature
        result = validate_signature("https://example.com/whatsapp", {}, "bad-sig")

    assert result is False


def test_validate_signature_no_token_fail_closed():
    """Missing auth token + no bypass flag → fail closed (False)."""
    with patch("app.services.twilio_client.get_settings") as mock_settings:
        mock_settings.return_value.twilio_auth_token = ""
        mock_settings.return_value.skip_twilio_signature_validation = False

        from app.services.twilio_client import validate_signature
        result = validate_signature("https://example.com/whatsapp", {}, "")

    assert result is False


def test_validate_signature_bypass_flag_allows():
    """Missing token + skip_twilio_signature_validation=True → returns True (dev bypass)."""
    with patch("app.services.twilio_client.get_settings") as mock_settings:
        mock_settings.return_value.twilio_auth_token = ""
        mock_settings.return_value.skip_twilio_signature_validation = True

        from app.services.twilio_client import validate_signature
        result = validate_signature("http://localhost/whatsapp", {}, "")

    assert result is True


def test_send_whatsapp_calls_twilio():
    """send_whatsapp creates a Twilio REST message and returns the SID."""
    with patch("app.services.twilio_client.get_settings") as mock_settings, \
         patch("app.services.twilio_client.Client") as mock_client_cls:

        mock_settings.return_value.twilio_account_sid = "ACtest"
        mock_settings.return_value.twilio_auth_token = "authtoken"
        mock_settings.return_value.twilio_whatsapp_from = "whatsapp:+14155238886"

        fake_message = MagicMock()
        fake_message.sid = "SM123"
        mock_client_cls.return_value.messages.create.return_value = fake_message

        from app.services.twilio_client import send_whatsapp
        sid = send_whatsapp("whatsapp:+5491112345678", "Hello!")

    assert sid == "SM123"
    mock_client_cls.return_value.messages.create.assert_called_once_with(
        from_="whatsapp:+14155238886",
        to="whatsapp:+5491112345678",
        body="Hello!",
    )
