"""Gemini → Groq → Hugging Face: scraped page → interview Q + ideal answer."""

from __future__ import annotations

import json
import re

import google.generativeai as genai

from app.services.groq_json import groq_chat_json
from app.services.hf_json import hf_chat_json


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _repair(bad: str) -> str:
    return f"""Return ONLY valid JSON with keys: page_summary (string), question_text (string), ideal_answer (string).
No markdown.

Broken:
{bad[:8000]}
"""


def _validate_web_pack(data: dict) -> dict:
    summary = (data.get("page_summary") or "").strip()
    q = (data.get("question_text") or "").strip()
    ideal = (data.get("ideal_answer") or "").strip()
    if not summary or not q or not ideal:
        raise ValueError("Model returned incomplete package")
    return {
        "page_summary": summary,
        "question_text": q,
        "ideal_answer": ideal,
    }


def _from_gemini(
    google_api_key: str,
    model_name: str,
    role: str,
    body: str,
    source_url: str,
) -> dict:
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(
        model_name,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    prompt = f"""You are an expert interview coach.

**Target role:** {role}

**Source URL (for context only; user may have scraped this page):**
{source_url}

**Extracted page text (may include interview Q&A lists, blog posts, or docs):**
{body}

**Tasks:**
1. page_summary: 2–4 sentences describing what the page content is about and how it relates to interviewing for the target role.
2. question_text: Pick or synthesize ONE clear interview question that fits the target role and is grounded in themes from the page.
3. ideal_answer: A strong sample answer (1–2 short paragraphs) a candidate could give.

Return JSON only: page_summary, question_text, ideal_answer.
"""
    r1 = model.generate_content(prompt)
    raw1 = (r1.text or "").strip()
    try:
        data = _extract_json(raw1)
    except json.JSONDecodeError:
        r2 = model.generate_content(_repair(raw1))
        data = _extract_json((r2.text or "").strip())
    return _validate_web_pack(data)


def _web_llm_prompt(role: str, body: str, source_url: str) -> str:
    return f"""You are an expert interview coach.

**Target role:** {role}

**Source URL:** {source_url}

**Extracted page text:**
{body}

**Tasks:**
1. page_summary: 2–4 sentences on what the page is about and how it relates to interviewing for the role.
2. question_text: ONE interview question for the role, grounded in the page.
3. ideal_answer: 1–2 short paragraphs, strong sample answer.

Return JSON with keys exactly: page_summary, question_text, ideal_answer (all strings).
"""


def _from_groq(
    groq_api_key: str,
    groq_model: str,
    role: str,
    body: str,
    source_url: str,
) -> dict:
    data = groq_chat_json(
        groq_api_key,
        groq_model,
        _web_llm_prompt(role, body, source_url),
        max_tokens=4096,
    )
    return _validate_web_pack(data)


def _from_hf(
    hf_api_key: str,
    hf_model: str,
    hf_base_url: str,
    role: str,
    body: str,
    source_url: str,
) -> dict:
    data = hf_chat_json(
        hf_api_key,
        hf_model,
        _web_llm_prompt(role, body, source_url),
        base_url=hf_base_url,
        max_tokens=4096,
    )
    return _validate_web_pack(data)


def generate_question_from_web_text(
    role: str,
    page_text: str,
    source_url: str,
    *,
    google_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash",
    groq_api_key: str | None = None,
    groq_model: str = "llama-3.3-70b-versatile",
    hf_api_key: str | None = None,
    hf_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
    hf_base_url: str = "https://router.huggingface.co/v1",
    text_max_chars: int = 14_000,
) -> dict:
    role = (role or "").strip().replace("{", "(").replace("}", ")")
    if not role:
        raise ValueError("Role is required")
    body = page_text.strip()
    if len(body) > text_max_chars:
        body = body[: text_max_chars - 3] + "..."

    g = (google_api_key or "").strip()
    gr = (groq_api_key or "").strip()
    hf = (hf_api_key or "").strip()
    if not g and not gr and not hf:
        raise ValueError(
            "Configure at least one of GOOGLE_API_KEY, GROQ_API_KEY, HUGGINGFACE_API_KEY"
        )

    errors: list[str] = []
    if g:
        try:
            return _from_gemini(g, gemini_model, role, body, source_url)
        except Exception as e:
            errors.append(f"gemini: {e}")
    if gr:
        try:
            return _from_groq(gr, groq_model, role, body, source_url)
        except Exception as e:
            errors.append(f"groq: {e}")
    if hf:
        try:
            return _from_hf(hf, hf_model, hf_base_url, role, body, source_url)
        except Exception as e:
            errors.append(f"huggingface: {e}")

    raise RuntimeError(" | ".join(errors) if errors else "All LLM providers failed")


def _validate_followup_web(data: dict) -> dict:
    q = (data.get("question_text") or "").strip()
    ideal = (data.get("ideal_answer") or "").strip()
    if not q or not ideal:
        raise ValueError("Model returned incomplete follow-up package")
    return {"question_text": q, "ideal_answer": ideal}


def _followup_web_prompt(
    role: str,
    body: str,
    source_url: str,
    page_summary: str,
    asked: list[str],
) -> str:
    prev = "\n".join(f"- {q[:500]}" for q in asked[:25]) or "(none yet)"
    return f"""You are an expert interview coach.

**Target role:** {role}
**Source URL:** {source_url}
**Page summary (this session):** {page_summary}

**Extracted page text (for grounding):**
{body}

**Questions already asked in this session—do NOT repeat or closely paraphrase:**
{prev}

**Task:** Write ONE NEW interview question for the role, still grounded in the page, covering a different angle or subtopic than the questions above.
**ideal_answer:** 1–2 short paragraphs—a strong sample answer.

Return JSON with keys exactly: question_text, ideal_answer (strings).
"""


def _followup_gemini(
    google_api_key: str,
    model_name: str,
    role: str,
    body: str,
    source_url: str,
    page_summary: str,
    asked: list[str],
) -> dict:
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(
        model_name,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    prompt = _followup_web_prompt(role, body, source_url, page_summary, asked)
    r1 = model.generate_content(prompt)
    raw1 = (r1.text or "").strip()
    try:
        data = _extract_json(raw1)
    except json.JSONDecodeError:
        r2 = model.generate_content(
            f"""Return ONLY valid JSON with keys question_text, ideal_answer. No markdown.
Broken:
{raw1[:8000]}
"""
        )
        data = _extract_json((r2.text or "").strip())
    return _validate_followup_web(data)


def generate_followup_web_question(
    role: str,
    page_text: str,
    source_url: str,
    page_summary: str,
    asked_questions: list[str],
    *,
    google_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash",
    groq_api_key: str | None = None,
    groq_model: str = "llama-3.3-70b-versatile",
    hf_api_key: str | None = None,
    hf_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
    hf_base_url: str = "https://router.huggingface.co/v1",
    text_max_chars: int = 14_000,
) -> dict:
    role = (role or "").strip().replace("{", "(").replace("}", ")")
    body = page_text.strip()
    if len(body) > text_max_chars:
        body = body[: text_max_chars - 3] + "..."

    g = (google_api_key or "").strip()
    gr = (groq_api_key or "").strip()
    hf = (hf_api_key or "").strip()
    if not g and not gr and not hf:
        raise ValueError(
            "Configure at least one of GOOGLE_API_KEY, GROQ_API_KEY, HUGGINGFACE_API_KEY"
        )

    errors: list[str] = []
    if g:
        try:
            return _followup_gemini(
                g, gemini_model, role, body, source_url, page_summary, asked_questions
            )
        except Exception as e:
            errors.append(f"gemini: {e}")
    if gr:
        try:
            data = groq_chat_json(
                gr,
                groq_model,
                _followup_web_prompt(
                    role, body, source_url, page_summary, asked_questions
                ),
                max_tokens=4096,
            )
            return _validate_followup_web(data)
        except Exception as e:
            errors.append(f"groq: {e}")
    if hf:
        try:
            data = hf_chat_json(
                hf_api_key,
                hf_model,
                _followup_web_prompt(
                    role, body, source_url, page_summary, asked_questions
                ),
                base_url=hf_base_url,
                max_tokens=4096,
            )
            return _validate_followup_web(data)
        except Exception as e:
            errors.append(f"huggingface: {e}")

    raise RuntimeError(" | ".join(errors) if errors else "All LLM providers failed")
