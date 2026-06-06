"""Normalize WhatsApp text/audio into plain text for the capture pipeline.

Synchronous port of the transcribe team's `whatsapp_transcription` module
(origin/main commits 94fa9a7, 548da37), adapted to run inside the capture
pipeline's threadpool worker (no asyncio). For audio voice notes it downloads
the Twilio media, transcodes to mp3 with ffmpeg (via imageio-ffmpeg), and
transcribes with OpenAI `gpt-4o-mini-transcribe`.
"""

import logging
import subprocess
import tempfile
from pathlib import Path

import httpx
import imageio_ffmpeg
from openai import OpenAI

from app.config import Settings

log = logging.getLogger(__name__)


class MessageNormalizationError(RuntimeError):
    """The payload has no text and no supported audio media."""


class TranscriptionError(RuntimeError):
    """Media could not be downloaded, transcoded, or transcribed."""


def normalize_message(form: dict, settings: Settings) -> str:
    """Return the message text: the body verbatim, or a transcript of audio media.

    Raises MessageNormalizationError when there's nothing usable to extract from.
    """
    body = (form.get("Body") or "").strip()
    media_count = _parse_int(form.get("NumMedia"))
    media_url = form.get("MediaUrl0") or ""
    content_type = form.get("MediaContentType0") or ""

    if media_count > 0:
        if media_url and content_type.startswith("audio/"):
            return transcribe_audio(media_url, content_type, settings)
        raise MessageNormalizationError("Only audio media is supported")

    if body:
        return body

    raise MessageNormalizationError("Message has no text or supported audio media")


def transcribe_audio(media_url: str, content_type: str, settings: Settings) -> str:
    audio_bytes = _download_twilio_media(media_url, settings)
    mp3_bytes = _convert_to_mp3(audio_bytes, content_type)
    transcript = _transcribe_mp3(mp3_bytes, settings).strip()
    if not transcript:
        raise TranscriptionError("Transcription returned empty text")
    log.info("Transcribed audio note (%d chars)", len(transcript))
    return transcript


def _download_twilio_media(media_url: str, settings: Settings) -> bytes:
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        raise TranscriptionError("Twilio credentials are required to download media")
    with httpx.Client(timeout=20) as client:
        response = client.get(
            media_url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise TranscriptionError("Twilio media download failed") from exc
    return response.content


def _convert_to_mp3(audio_bytes: bytes, content_type: str) -> bytes:
    suffix = _suffix_for_content_type(content_type)
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / f"input{suffix}"
        output_path = Path(tmpdir) / "output.mp3"
        input_path.write_bytes(audio_bytes)
        command = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise TranscriptionError("Audio conversion failed")
        return output_path.read_bytes()


def _transcribe_mp3(mp3_bytes: bytes, settings: Settings) -> str:
    if not settings.openai_api_key:
        raise TranscriptionError("OPENAI_API_KEY is required for transcription")
    client = OpenAI(api_key=settings.openai_api_key)
    with tempfile.NamedTemporaryFile(suffix=".mp3") as audio_file:
        audio_file.write(mp3_bytes)
        audio_file.flush()
        with open(audio_file.name, "rb") as file_handle:
            result = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=file_handle,
            )
    return result.text


def _suffix_for_content_type(content_type: str) -> str:
    normalized = content_type.split(";")[0].strip().lower()
    return {
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".mp4",
        "audio/m4a": ".m4a",
        "audio/ogg": ".ogg",
        "audio/opus": ".ogg",
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/webm": ".webm",
    }.get(normalized, ".audio")


def _parse_int(value) -> int:
    try:
        return int(value or "0")
    except (TypeError, ValueError):
        return 0
