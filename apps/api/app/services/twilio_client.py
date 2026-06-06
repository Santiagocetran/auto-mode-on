"""Twilio helpers: signature validation + WhatsApp send."""

import logging

from twilio.request_validator import RequestValidator
from twilio.rest import Client

from app.config import get_settings

log = logging.getLogger(__name__)


def validate_signature(url: str, params: dict, signature_header: str) -> bool:
    """Return True if the Twilio signature is valid for the given URL and form params.

    Fail-closed when TWILIO_AUTH_TOKEN is set: an invalid or missing signature
    returns False. In local dev, set skip_twilio_signature_validation=True to bypass.
    """
    settings = get_settings()
    if not settings.twilio_auth_token:
        if settings.skip_twilio_signature_validation:
            log.warning("Twilio signature validation bypassed (dev mode, no auth token)")
            return True
        log.error("TWILIO_AUTH_TOKEN not set and bypass not enabled — rejecting")
        return False
    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(url, params, signature_header)


def send_whatsapp(to: str, body: str) -> str:
    """Send a WhatsApp message via Twilio REST. Returns the message SID."""
    settings = get_settings()
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    message = client.messages.create(
        from_=settings.twilio_whatsapp_from,
        to=to,
        body=body,
    )
    log.info("Sent WhatsApp to=%s sid=%s", to, message.sid)
    return message.sid
