"""Tests for app.services.transcription (no network / no ffmpeg calls)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services import transcription
from app.services.transcription import (
    MessageNormalizationError,
    TranscriptionError,
    normalize_message,
)

SETTINGS = MagicMock(twilio_account_sid="AC", twilio_auth_token="tok", openai_api_key="sk")


def test_text_message_returns_body():
    form = {"Body": "Yo me encargo del informe", "NumMedia": "0"}
    assert normalize_message(form, SETTINGS) == "Yo me encargo del informe"


def test_empty_message_raises():
    with pytest.raises(MessageNormalizationError):
        normalize_message({"Body": "", "NumMedia": "0"}, SETTINGS)


def test_non_audio_media_raises():
    form = {"Body": "", "NumMedia": "1", "MediaUrl0": "https://x/img", "MediaContentType0": "image/jpeg"}
    with pytest.raises(MessageNormalizationError):
        normalize_message(form, SETTINGS)


def test_audio_media_is_transcribed():
    form = {"Body": "", "NumMedia": "1", "MediaUrl0": "https://x/a.ogg", "MediaContentType0": "audio/ogg"}
    with patch.object(transcription, "_download_twilio_media", return_value=b"audio"), \
         patch.object(transcription, "_convert_to_mp3", return_value=b"mp3"), \
         patch.object(transcription, "_transcribe_mp3", return_value="comprar pintura para el taller"):
        assert normalize_message(form, SETTINGS) == "comprar pintura para el taller"


def test_empty_transcript_raises():
    with patch.object(transcription, "_download_twilio_media", return_value=b"audio"), \
         patch.object(transcription, "_convert_to_mp3", return_value=b"mp3"), \
         patch.object(transcription, "_transcribe_mp3", return_value="   "):
        with pytest.raises(TranscriptionError):
            transcription.transcribe_audio("https://x/a.ogg", "audio/ogg", SETTINGS)
