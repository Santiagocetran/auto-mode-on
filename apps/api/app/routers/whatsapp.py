"""Inbound WhatsApp webhook — thin adapter.

Business logic lives in app.services.capture. This router only:
  1. Reads the form-encoded body (Twilio posts application/x-www-form-urlencoded)
  2. Validates the Twilio signature against the configured public URL
  3. Delegates to capture.handle_inbound
  4. Returns an empty 200 (all replies go out via REST, not TwiML)
"""

import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.services import capture
from app.services.twilio_client import validate_signature

log = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("")
async def inbound(request: Request) -> Response:
    settings = get_settings()

    # Twilio posts application/x-www-form-urlencoded
    form = await request.form()
    form_data = dict(form)

    # Build exact public URL for Twilio signature validation.
    # Reconstructing from request headers is fragile behind tunnels; use the
    # explicit public_webhook_base_url setting instead.
    base_url = settings.public_webhook_base_url.rstrip("/")
    webhook_url = f"{base_url}/whatsapp"

    signature = request.headers.get("X-Twilio-Signature", "")
    if not validate_signature(webhook_url, form_data, signature):
        log.warning("Invalid Twilio signature from %s", getattr(request.client, "host", "?"))
        return PlainTextResponse("Forbidden", status_code=403)

    # handle_inbound does blocking I/O (OpenAI + Supabase + Twilio). Run it in a
    # threadpool so it never blocks the async event loop.
    try:
        await run_in_threadpool(capture.handle_inbound, form_data)
    except Exception:
        log.exception("Unhandled error in WhatsApp capture pipeline")

    return Response(status_code=200)
