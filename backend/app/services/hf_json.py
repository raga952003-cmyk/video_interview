"""Hugging Face Serverless Inference via OpenAI-compatible chat API."""

from __future__ import annotations

import json
import re


def _strip_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return json.loads(t)


def hf_chat_json(
    api_key: str,
    model: str,
    user_prompt: str,
    *,
    base_url: str | None = None,
    max_tokens: int = 4096,
) -> dict:
    from openai import OpenAI

    base = (base_url or "https://router.huggingface.co/v1").rstrip("/")
    client = OpenAI(base_url=base, api_key=api_key)
    messages = [
        {
            "role": "system",
            "content": "You output a single valid JSON object only. No markdown fences.",
        },
        {"role": "user", "content": user_prompt},
    ]
    try:
        r = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
    except Exception:
        r = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=max_tokens,
        )
    text = (r.choices[0].message.content or "").strip()
    return _strip_json(text)
