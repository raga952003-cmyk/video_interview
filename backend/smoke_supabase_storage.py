"""
Quick check: Supabase Storage upload + signed URL + delete.

Loads .env from backend/ or repo root (same as run.py). Does not print secrets.

Usage (from backend/):
  python smoke_supabase_storage.py
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_root = Path(__file__).resolve().parent
load_dotenv(_root / ".env")
load_dotenv(_root.parent / ".env")


def main() -> None:
    from app import create_app
    from app.services.supabase_storage import (
        recording_storage_supabase_ready,
        remove_recording_object,
        signed_recording_url,
        upload_recording,
    )

    app = create_app()
    cfg = dict(app.config)
    url = (cfg.get("SUPABASE_URL") or "").strip()
    key = (cfg.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    bucket = (cfg.get("SUPABASE_STORAGE_BUCKET") or "").strip()

    host = url.split("//")[-1].split("/")[0] if url else "-"
    print("SUPABASE_URL set:", bool(url), "| host:", host)
    print("SUPABASE_SERVICE_ROLE_KEY set:", bool(key))
    print("SUPABASE_STORAGE_BUCKET:", bucket or "(empty — will not be ready)")

    if not recording_storage_supabase_ready(cfg):
        print("\nNot ready: need SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY set (bucket defaults to video).")
        raise SystemExit(1)

    path = "recordings/_smoke_test.txt"
    data = b"smoke-test"
    upload_recording(cfg, path, data, "text/plain")
    print("\nUpload: OK")
    signed = signed_recording_url(cfg, path, 120)
    print("Signed URL:", "OK" if signed else "FAILED")
    remove_recording_object(cfg, path)
    print("Remove: OK")
    print("\nSupabase Storage smoke test passed.")


if __name__ == "__main__":
    main()
