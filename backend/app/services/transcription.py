from __future__ import annotations

from io import BytesIO


def _read_upload(file_storage) -> tuple[bytes, str]:
    file_storage.stream.seek(0)
    raw = file_storage.read()
    name = file_storage.filename or "audio.webm"
    return raw, name


def _openai_whisper(api_key: str, raw: bytes, filename: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    buf = BytesIO(raw)
    buf.name = filename
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=buf,
    )
    text = (transcript.text or "").strip()
    if not text:
        raise ValueError("OpenAI transcription was empty")
    return text


def _groq_whisper(api_key: str, raw: bytes, filename: str, model: str) -> str:
    from groq import Groq

    client = Groq(api_key=api_key)
    transcript = client.audio.transcriptions.create(
        file=(filename, raw),
        model=model,
    )
    text = (getattr(transcript, "text", None) or "").strip()
    if not text:
        raise ValueError("Groq transcription was empty")
    return text


def transcribe_audio(
    file_storage,
    *,
    openai_api_key: str | None = None,
    groq_api_key: str | None = None,
    groq_whisper_model: str = "whisper-large-v3",
) -> str:
    """
    Try OpenAI Whisper first; on failure (quota, error), fall back to Groq Whisper
    if GROQ_API_KEY is set.
    """
    raw, filename = _read_upload(file_storage)
    oa = (openai_api_key or "").strip()
    gq = (groq_api_key or "").strip()

    if not oa and not gq:
        raise ValueError(
            "Configure OPENAI_API_KEY and/or GROQ_API_KEY for speech-to-text"
        )

    errors: list[str] = []
    if oa:
        try:
            return _openai_whisper(oa, raw, filename)
        except Exception as e:
            errors.append(f"openai_whisper: {e}")
    if gq:
        try:
            return _groq_whisper(gq, raw, filename, groq_whisper_model)
        except Exception as e:
            errors.append(f"groq_whisper: {e}")

    raise RuntimeError(
        " | ".join(errors) if errors else "Speech-to-text failed for all providers"
    )
