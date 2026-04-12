"""Optional Supabase Storage for interview recordings (upload + signed download URLs)."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def recording_storage_supabase_ready(config: dict) -> bool:
    url = (config.get("SUPABASE_URL") or "").strip()
    key = (config.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    bucket = (config.get("SUPABASE_STORAGE_BUCKET") or "").strip()
    if not (url and key and bucket):
        return False
    try:
        import supabase  # noqa: F401
    except ImportError:
        return False
    return True


def _normalize_object_path(object_path: str) -> str:
    return object_path.lstrip("/").replace("\\", "/")


def _client(config: dict) -> Any:
    from supabase import create_client

    url = (config.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (config.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return create_client(url, key)


def upload_recording(
    config: dict, object_path: str, data: bytes, content_type: str
) -> None:
    bucket = (config.get("SUPABASE_STORAGE_BUCKET") or "").strip()
    path = _normalize_object_path(object_path)
    client = _client(config)
    client.storage.from_(bucket).upload(
        path,
        data,
        file_options={
            "content-type": content_type or "application/octet-stream",
            "upsert": "true",
        },
    )


def remove_recording_object(config: dict, object_path: str) -> None:
    bucket = (config.get("SUPABASE_STORAGE_BUCKET") or "").strip()
    path = _normalize_object_path(object_path)
    client = _client(config)
    client.storage.from_(bucket).remove([path])


def signed_recording_url(
    config: dict, object_path: str, expires_in: int = 3600
) -> str | None:
    bucket = (config.get("SUPABASE_STORAGE_BUCKET") or "").strip()
    path = _normalize_object_path(object_path)
    try:
        client = _client(config)
        resp = client.storage.from_(bucket).create_signed_url(path, expires_in)
    except Exception:
        log.exception("supabase create_signed_url failed for %s", path)
        return None
    if isinstance(resp, dict):
        return resp.get("signedURL") or resp.get("signedUrl")
    return None
