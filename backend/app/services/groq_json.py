"""Groq Chat Completions with JSON output."""

from __future__ import annotations

import json


def groq_chat_json(
    api_key: str,
    model: str,
    user_prompt: str,
    *,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> dict:
    from groq import Groq

    client = Groq(api_key=api_key)
    r = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You output a single valid JSON object only. No markdown fences or commentary.",
            },
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    text = (r.choices[0].message.content or "").strip()
    return json.loads(text)
