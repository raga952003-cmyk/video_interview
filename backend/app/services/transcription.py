from __future__ import annotations

import os
import tempfile
from io import BytesIO

# Lazy singleton: (model_size, device, compute_type) -> WhisperModel
_local_model_cache: dict[tuple[str, str, str], object] = {}


def _read_upload(file_storage) -> tuple[bytes, str]:
    file_storage.stream.seek(0)
    raw = file_storage.read()
    name = file_storage.filename or "audio.webm"
    return raw, name


def _get_local_whisper_model(model_size: str, device: str, compute_type: str):
    key = (model_size, device, compute_type)
    if key not in _local_model_cache:
        from faster_whisper import WhisperModel

        _local_model_cache[key] = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )
    return _local_model_cache[key]


def _local_faster_whisper(
    raw: bytes,
    filename: str,
    *,
    model_size: str,
    device: str,
    compute_type: str,
) -> str:
    model = _get_local_whisper_model(model_size, device, compute_type)
    ext = os.path.splitext(filename)[1] or ".webm"
    if ext.lower() not in (
        ".webm",
        ".wav",
        ".mp3",
        ".m4a",
        ".ogg",
        ".flac",
        ".mp4",
        ".mkv",
    ):
        ext = ".webm"
    path = None
    fd = None
    try:
        fd, path = tempfile.mkstemp(suffix=ext)
        os.write(fd, raw)
        os.close(fd)
        fd = None
        segments, _info = model.transcribe(path, vad_filter=True)
        parts = [s.text for s in segments]
        text = " ".join(p.strip() for p in parts).strip()
        if not text:
            raise ValueError("Local Whisper returned an empty transcript")
        return text
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if path and os.path.isfile(path):
            try:
                os.unlink(path)
            except OSError:
                pass


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
    local_whisper: bool = False,
    local_whisper_model: str = "base",
    local_whisper_device: str = "cpu",
    local_whisper_compute_type: str = "int8",
) -> str:
    """
    If local_whisper is True, try faster-whisper (open-source) first.
    Then OpenAI Whisper, then Groq Whisper when API keys are set.
    """
    raw, filename = _read_upload(file_storage)
    oa = (openai_api_key or "").strip()
    gq = (groq_api_key or "").strip()

    if not local_whisper and not oa and not gq:
        raise ValueError(
            "Enable LOCAL_WHISPER=1 or set OPENAI_API_KEY and/or GROQ_API_KEY "
            "for speech-to-text"
        )

    errors: list[str] = []

    if local_whisper:
        try:
            return _local_faster_whisper(
                raw,
                filename,
                model_size=local_whisper_model,
                device=local_whisper_device,
                compute_type=local_whisper_compute_type,
            )
        except Exception as e:
            errors.append(f"local_whisper: {e}")

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
