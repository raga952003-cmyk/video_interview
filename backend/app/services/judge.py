import json
import re

import google.generativeai as genai

from app.services.groq_json import groq_chat_json
from app.services.hf_json import hf_chat_json


def _escape_for_prompt(s: str, max_len: int = 12000) -> str:
    t = (s or "").strip()
    if len(t) > max_len:
        t = t[: max_len - 3] + "..."
    return t.replace("{", "{{").replace("}", "}}")


def _build_prompt(question_text: str, user_answer: str, ideal_answer: str) -> str:
    q = _escape_for_prompt(question_text)
    u = _escape_for_prompt(user_answer)
    i = _escape_for_prompt(ideal_answer)
    return f"""You are an expert technical interview coach. Your task is to evaluate a candidate's answer to an interview question by strictly comparing it to the provided ideal answer. Your response must be in a structured JSON format.

**THE CONTEXT:**

*   **Interview Question Asked:**
    "{q}"

*   **Candidate's Transcribed Answer:**
    "{u}"

*   **Ideal Answer (Ground Truth for Comparison):**
    "{i}"

**YOUR TASK:**

Analyze the candidate's answer based on how well it aligns with the "Ideal Answer." Provide a score from 1 (poor) to 5 (excellent) for each of the following criteria. Then, provide concise, actionable feedback.

**Output the following JSON object and nothing else:**

{{
  "scores": {{
    "clarity": <Integer score 1-5 for clarity and confidence>,
    "correctness": <Integer score 1-5 for technical accuracy compared to the ideal answer>,
    "completeness": <Integer score 1-5 based on how many key points from the ideal answer were mentioned>
  }},
  "improved_answer_example": "<2-4 sentences: how the candidate could phrase a stronger answer, in first person (I would…), incorporating key ideas from the ideal answer>",
  "feedback_summary": "<One sentence summary>",
  "suggestions_for_improvement": "<Actionable advice>",
  "perfect_answer": "<Exact full text of the Ideal Answer section above, verbatim>"
}}
"""


def _plain_trunc(s: str, max_len: int = 12000) -> str:
    t = (s or "").strip()
    if len(t) > max_len:
        t = t[: max_len - 3] + "..."
    return t


def _build_groq_judge_prompt(
    question_text: str, user_answer: str, ideal_answer: str
) -> str:
    q = _plain_trunc(question_text)
    u = _plain_trunc(user_answer)
    i = _plain_trunc(ideal_answer)
    return f"""You are an expert interview coach. Compare the candidate's spoken answer to the ideal answer.

Interview question:
{q}

Candidate answer (transcribed):
{u}

Ideal answer:
{i}

Return JSON with keys:
- scores: object with integers 1-5 only: clarity, correctness, completeness
- improved_answer_example: string, 2-4 sentences, first person, stronger phrasing aligned with ideal answer
- feedback_summary: string, one sentence
- suggestions_for_improvement: string
- perfect_answer: string, copy the ideal answer text verbatim

JSON only."""


def _repair_prompt(bad_text: str) -> str:
    return f"""The following text was supposed to be a single valid JSON object with keys: scores (with clarity, correctness, completeness integers 1-5), improved_answer_example, feedback_summary, suggestions_for_improvement, perfect_answer.
Return ONLY valid JSON, no markdown fences, no commentary.

Broken output:
{bad_text[:8000]}
"""


def _parse_scores(obj: dict) -> dict:
    scores = obj.get("scores") or {}
    out = {}
    for k in ("clarity", "correctness", "completeness"):
        v = scores.get(k)
        if v is None:
            raise ValueError(f"Missing score: {k}")
        n = int(v)
        if n < 1 or n > 5:
            raise ValueError(f"Score {k} out of range")
        out[k] = n
    return out


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def validate_feedback_payload(data: dict, ideal_fallback: str) -> dict:
    scores = _parse_scores(data)
    improved = (data.get("improved_answer_example") or "").strip()
    summary = (data.get("feedback_summary") or "").strip()
    suggestions = (data.get("suggestions_for_improvement") or "").strip()
    perfect = (data.get("perfect_answer") or "").strip() or ideal_fallback
    if not improved or not summary or not suggestions:
        raise ValueError("Missing feedback fields")
    return {
        "scores": scores,
        "improved_answer_example": improved,
        "feedback_summary": summary,
        "suggestions_for_improvement": suggestions,
        "perfect_answer": perfect,
    }


def _analyze_gemini(
    google_api_key: str,
    model_name: str,
    question_text: str,
    user_transcribed: str,
    ideal_answer: str,
) -> dict:
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(
        model_name,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    prompt = _build_prompt(question_text, user_transcribed, ideal_answer)
    r1 = model.generate_content(prompt)
    raw1 = (r1.text or "").strip()
    try:
        payload = _extract_json(raw1)
        return validate_feedback_payload(payload, ideal_answer)
    except (json.JSONDecodeError, ValueError, TypeError):
        r2 = model.generate_content(_repair_prompt(raw1))
        raw2 = (r2.text or "").strip()
        payload = _extract_json(raw2)
        return validate_feedback_payload(payload, ideal_answer)


def _analyze_groq(
    groq_api_key: str,
    groq_model: str,
    question_text: str,
    user_transcribed: str,
    ideal_answer: str,
) -> dict:
    prompt = _build_groq_judge_prompt(
        question_text, user_transcribed, ideal_answer
    )
    payload = groq_chat_json(groq_api_key, groq_model, prompt, max_tokens=2048)
    return validate_feedback_payload(payload, ideal_answer)


def _analyze_hf(
    hf_api_key: str,
    hf_model: str,
    hf_base_url: str,
    question_text: str,
    user_transcribed: str,
    ideal_answer: str,
) -> dict:
    prompt = _build_groq_judge_prompt(
        question_text, user_transcribed, ideal_answer
    )
    payload = hf_chat_json(
        hf_api_key,
        hf_model,
        prompt,
        base_url=hf_base_url,
        max_tokens=2048,
    )
    return validate_feedback_payload(payload, ideal_answer)


def analyze_answer(
    question_text: str,
    user_transcribed: str,
    ideal_answer: str,
    *,
    google_api_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash",
    groq_api_key: str | None = None,
    groq_model: str = "llama-3.3-70b-versatile",
    hf_api_key: str | None = None,
    hf_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
    hf_base_url: str = "https://router.huggingface.co/v1",
) -> dict:
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
            return _analyze_gemini(
                g, gemini_model, question_text, user_transcribed, ideal_answer
            )
        except Exception as e:
            errors.append(f"gemini: {e}")
    if gr:
        try:
            return _analyze_groq(
                gr, groq_model, question_text, user_transcribed, ideal_answer
            )
        except Exception as e:
            errors.append(f"groq: {e}")
    if hf:
        try:
            return _analyze_hf(
                hf,
                hf_model,
                hf_base_url,
                question_text,
                user_transcribed,
                ideal_answer,
            )
        except Exception as e:
            errors.append(f"huggingface: {e}")

    raise RuntimeError(" | ".join(errors) if errors else "All LLM providers failed")
