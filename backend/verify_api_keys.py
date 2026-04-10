"""Test API keys from .env (project root or backend/). Does not print secrets."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

_root = Path(__file__).resolve().parent
load_dotenv(_root / ".env")
load_dotenv(_root.parent / ".env")


def main() -> int:
    import os

    failures = 0

    openai_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    google_key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    mistral_key = (os.environ.get("MISTRAL_API_KEY") or "").strip()
    qdrant_url = (os.environ.get("QDRANT_URL") or "").strip().rstrip("/")
    qdrant_key = (os.environ.get("QDRANT_API_KEY") or "").strip()

    # --- OpenAI ---
    if not openai_key:
        print("OPENAI_API_KEY: NOT SET")
        failures += 1
    else:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_key)
            list(client.models.list())
            print("OPENAI_API_KEY: OK (authenticated)")
        except Exception as e:
            print(f"OPENAI_API_KEY: FAIL — {e}")
            failures += 1

    # --- Google Gemini ---
    if not google_key:
        print("GOOGLE_API_KEY: NOT SET")
        failures += 1
    else:
        try:
            import google.generativeai as genai

            genai.configure(api_key=google_key)
            model_name = (os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash").strip()
            model = genai.GenerativeModel(model_name)
            r = model.generate_content(
                "Reply with exactly: ok",
                generation_config=genai.GenerationConfig(max_output_tokens=8),
            )
            text = (r.text or "").strip().lower()
            if not text:
                print("GOOGLE_API_KEY: FAIL — empty model response")
                failures += 1
            else:
                print(f"GOOGLE_API_KEY: OK (model {model_name} responded)")
        except Exception as e:
            err = str(e).lower()
            if "resource exhausted" in err or "quota" in err or "429" in str(e):
                print("GOOGLE_API_KEY: OK (key works) — quota/rate limit hit; retry later or enable billing")
            elif "404" in str(e) or "not found" in err:
                print(f"GOOGLE_API_KEY: FAIL — model {model_name!r} unavailable for this key/API")
                print("         Hint: set GEMINI_MODEL (e.g. gemini-2.0-flash, gemini-2.5-flash-preview)")
                failures += 1
            else:
                print(f"GOOGLE_API_KEY: FAIL — {e}")
                failures += 1

    # --- Groq ---
    if not groq_key:
        print("GROQ_API_KEY: NOT SET (optional)")
    else:
        try:
            from groq import Groq

            g = Groq(api_key=groq_key)
            g.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Say hi"}],
                max_tokens=5,
            )
            print("GROQ_API_KEY: OK")
        except Exception as e:
            print(f"GROQ_API_KEY: FAIL — {e}")
            failures += 1

    # --- Mistral ---
    if not mistral_key:
        print("MISTRAL_API_KEY: NOT SET (optional)")
    else:
        try:
            import urllib.request

            req = urllib.request.Request(
                "https://api.mistral.ai/v1/models",
                headers={"Authorization": f"Bearer {mistral_key}"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
            print("MISTRAL_API_KEY: OK")
        except Exception as e:
            if "503" in str(e):
                print("MISTRAL_API_KEY: FAIL — Mistral API returned 503 (try again; service may be busy)")
            else:
                print(f"MISTRAL_API_KEY: FAIL — {e}")
            failures += 1

    # --- Qdrant Cloud ---
    if not qdrant_url or not qdrant_key:
        print("QDRANT: NOT SET (optional QDRANT_URL + QDRANT_API_KEY)")
    else:
        try:
            from qdrant_client import QdrantClient

            qc = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=20)
            qc.get_collections()
            print("QDRANT: OK (cluster reachable)")
        except Exception as e:
            err = str(e).lower()
            if "timed out" in err or "timeout" in err:
                print(
                    "QDRANT: SKIP — timeout from this network (run verify on your PC; check VPN/firewall)"
                )
            else:
                print(f"QDRANT: FAIL — {e}")
                failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
