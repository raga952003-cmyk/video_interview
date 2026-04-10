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


def _repair_prompt(bad_text: str) -> str:
    return f"""Return ONLY valid JSON with keys: resume_summary (string), question_text (string), ideal_answer (string).
No markdown fences.

Broken output:
{bad_text[:8000]}
"""


def _from_gemini(
    google_api_key: str, model_name: str, role_safe: str, body: str
) -> dict:
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(
        model_name,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    prompt = f"""You are an expert hiring manager and interview coach.

**Target role the candidate is interviewing for:** {role_safe}

**Resume / CV text:**
{body}

**Tasks:**
1. Write resume_summary: 2–4 sentences capturing their strongest relevant experience for this role (no bullet list).
2. Write question_text: ONE focused interview question (behavioral or technical) that is specific to their background and the role—not generic.
3. Write ideal_answer: A strong sample answer (one or two short paragraphs) a well-prepared candidate might give, aligned with typical expectations for this role.

Return JSON only with keys: resume_summary, question_text, ideal_answer.
"""
    r1 = model.generate_content(prompt)
    raw1 = (r1.text or "").strip()
    try:
        data = _extract_json(raw1)
    except json.JSONDecodeError:
        r2 = model.generate_content(_repair_prompt(raw1))
        data = _extract_json((r2.text or "").strip())
    return _validate_resume_pack(data)


def _resume_llm_prompt(role_safe: str, body: str) -> str:
    return f"""You are an expert hiring manager and interview coach.

**Target role the candidate is interviewing for:** {role_safe}

**Resume / CV text:**
{body}

**Tasks:**
1. resume_summary: 2–4 sentences capturing their strongest relevant experience for this role (no bullet list).
2. question_text: ONE focused interview question (behavioral or technical) specific to their background and the role.
3. ideal_answer: A strong sample answer (one or two short paragraphs) a well-prepared candidate might give.

Return a JSON object with keys exactly: resume_summary, question_text, ideal_answer (all strings).
"""


def _from_groq(groq_api_key: str, groq_model: str, role_safe: str, body: str) -> dict:
    data = groq_chat_json(
        groq_api_key, groq_model, _resume_llm_prompt(role_safe, body), max_tokens=4096
    )
    return _validate_resume_pack(data)


def _from_hf(
    hf_api_key: str,
    hf_model: str,
    hf_base_url: str,
    role_safe: str,
    body: str,
) -> dict:
    data = hf_chat_json(
        hf_api_key,
        hf_model,
        _resume_llm_prompt(role_safe, body),
        base_url=hf_base_url,
        max_tokens=4096,
    )
    return _validate_resume_pack(data)


def _validate_resume_pack(data: dict) -> dict:
    summary = (data.get("resume_summary") or "").strip()
    q = (data.get("question_text") or "").strip()
    ideal = (data.get("ideal_answer") or "").strip()
    if not summary or not q or not ideal:
        raise ValueError("Model returned incomplete question package")
    return {
        "resume_summary": summary,
        "question_text": q,
        "ideal_answer": ideal,
    }


def generate_interview_from_resume(
    role: str,
    resume_text: str,
    *,
    google_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash",
    groq_api_key: str | None = None,
    groq_model: str = "llama-3.3-70b-versatile",
    hf_api_key: str | None = None,
    hf_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
    hf_base_url: str = "https://router.huggingface.co/v1",
    resume_max_chars: int = 14000,
) -> dict:
    role = (role or "").strip()
    if not role:
        raise ValueError("Role is required")
    body = resume_text.strip()
    if len(body) > resume_max_chars:
        body = body[: resume_max_chars - 3] + "..."
    role_safe = role.replace("{", "(").replace("}", ")")

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
            return _from_gemini(g, gemini_model, role_safe, body)
        except Exception as e:
            errors.append(f"gemini: {e}")
    if gr:
        try:
            return _from_groq(gr, groq_model, role_safe, body)
        except Exception as e:
            errors.append(f"groq: {e}")
    if hf:
        try:
            return _from_hf(hf, hf_model, hf_base_url, role_safe, body)
        except Exception as e:
            errors.append(f"huggingface: {e}")

    raise RuntimeError(" | ".join(errors) if errors else "All LLM providers failed")
