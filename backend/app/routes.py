import hmac
import os
import secrets
import uuid
from io import BytesIO

from flask import Blueprint, current_app, jsonify, redirect, request, send_file
from sqlalchemy import func, select
from werkzeug.datastructures import FileStorage

from app.limiter_ext import limiter
from app.models import InterviewRecording, InterviewSession, Question
from app.services.judge import analyze_answer
from app.services.question_from_resume import (
    generate_resume_intro_pack,
    generate_resume_technical_question,
)
from app.services.question_from_web import (
    generate_followup_web_question,
    generate_question_from_web_text,
)
from app.services.resume import extract_text_from_upload
from app.services.transcription import transcribe_audio
from app.services.supabase_storage import (
    recording_storage_supabase_ready,
    remove_recording_object,
    signed_recording_url,
    upload_recording,
)
from app.services.web_scrape import fetch_page_text

bp = Blueprint("api", __name__)

LLM_KEY_FIX = (
    "On Render: Web Service → Environment → add GOOGLE_API_KEY (Google AI Studio) "
    "or GROQ_API_KEY or HUGGINGFACE_API_KEY — names must match exactly. "
    "Save, then Manual Deploy → Deploy latest commit."
)


def _cfg_strip(app, key: str) -> str:
    return (app.config.get(key) or "").strip()


def _llm_configured(app) -> bool:
    return bool(
        _cfg_strip(app, "GOOGLE_API_KEY")
        or _cfg_strip(app, "GROQ_API_KEY")
        or _cfg_strip(app, "HUGGINGFACE_API_KEY")
    )


def _llm_status_dict(app) -> dict:
    return {
        "GOOGLE_API_KEY": bool(_cfg_strip(app, "GOOGLE_API_KEY")),
        "GROQ_API_KEY": bool(_cfg_strip(app, "GROQ_API_KEY")),
        "HUGGINGFACE_API_KEY": bool(_cfg_strip(app, "HUGGINGFACE_API_KEY")),
    }


def _admin_key_ok() -> bool:
    exp = _cfg_strip(current_app, "ADMIN_API_KEY")
    if not exp:
        return False
    got = (request.headers.get("X-Admin-Key") or "").strip()
    if len(got) != len(exp):
        return False
    return hmac.compare_digest(got.encode("utf-8"), exp.encode("utf-8"))


def _recording_token_ok(got: str, stored: str) -> bool:
    if not got or not stored or len(got) != len(stored):
        return False
    return hmac.compare_digest(got.encode("ascii"), stored.encode("ascii"))


def _need_llm_response(app):
    return jsonify(
        {
            "error": "Server needs at least one LLM key: GOOGLE_API_KEY, GROQ_API_KEY, or HUGGINGFACE_API_KEY",
            "configured": _llm_status_dict(app),
            "fix": LLM_KEY_FIX,
        }
    ), 503


def _session():
    return current_app.extensions["Session"]()


def _resolve_question(s, qid: uuid.UUID):
    """Return (question_text, ideal_answer, source_tag)."""
    q = s.get(Question, qid)
    if q:
        return q.question_text, q.scraped_ideal_answer, "bank"
    sess = s.get(InterviewSession, qid)
    if sess:
        tag = "web" if (sess.source_url or "").strip() else "resume"
        return sess.question_text, sess.ideal_answer, tag
    return None, None, None


@bp.route("/health", methods=["GET"])
def health():
    db_ok = False
    try:
        s = _session()
        s.execute(select(1)).scalar_one()
        db_ok = True
    except Exception:
        pass
    keys = {
        "openai_configured": bool(_cfg_strip(current_app, "OPENAI_API_KEY")),
        "gemini_configured": bool(_cfg_strip(current_app, "GOOGLE_API_KEY")),
        "groq_configured": bool(_cfg_strip(current_app, "GROQ_API_KEY")),
        "huggingface_configured": bool(
            _cfg_strip(current_app, "HUGGINGFACE_API_KEY")
        ),
        "local_whisper_enabled": bool(current_app.config.get("LOCAL_WHISPER")),
        "admin_api_configured": bool(_cfg_strip(current_app, "ADMIN_API_KEY")),
        "supabase_recording_storage_ready": recording_storage_supabase_ready(
            current_app.config
        ),
    }
    llm_ready = _llm_configured(current_app)
    body = {
        "status": "ok",
        "database": db_ok,
        "llm_ready": llm_ready,
        **keys,
    }
    if not llm_ready:
        body["fix"] = LLM_KEY_FIX
    return jsonify(body)


@bp.route("/roles", methods=["GET"])
def roles():
    s = _session()
    rows = s.execute(
        select(Question.role_category).distinct().order_by(Question.role_category)
    ).all()
    return jsonify({"roles": [r[0] for r in rows]})


@bp.post("/prepare-from-resume")
@limiter.limit("20 per hour")
def prepare_from_resume():
    if not _llm_configured(current_app):
        return _need_llm_response(current_app)

    role = (request.form.get("role") or "").strip()
    if not role:
        return jsonify({"error": "Missing role (enter your target job title)"}), 400
    if len(role) > 500:
        return jsonify({"error": "Role is too long"}), 400

    if "resume" not in request.files or not request.files["resume"].filename:
        return jsonify({"error": "Missing resume file"}), 400

    try:
        resume_text = extract_text_from_upload(request.files["resume"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        current_app.logger.exception("resume parse failed")
        return jsonify({"error": "Could not read resume file"}), 400

    try:
        pack = generate_resume_intro_pack(
            role,
            resume_text,
            google_api_key=current_app.config.get("GOOGLE_API_KEY"),
            gemini_model=current_app.config["GEMINI_MODEL"],
            groq_api_key=current_app.config.get("GROQ_API_KEY"),
            groq_model=current_app.config["GROQ_MODEL"],
            hf_api_key=current_app.config.get("HUGGINGFACE_API_KEY"),
            hf_model=current_app.config["HUGGINGFACE_MODEL"],
            hf_base_url=current_app.config["HUGGINGFACE_BASE_URL"],
        )
    except Exception as e:
        current_app.logger.exception("question gen failed")
        return jsonify(
            {"error": "AI could not generate a question", "detail": str(e)}
        ), 503

    snap = resume_text.strip()
    if len(snap) > 12000:
        snap = snap[:11997] + "..."

    sid = uuid.uuid4()
    s = _session()
    s.add(
        InterviewSession(
            session_id=sid,
            role_text=role[:512],
            resume_summary=pack["resume_summary"],
            question_text=pack["question_text"],
            ideal_answer=pack["ideal_answer"],
            source_url=None,
            interview_run_id=sid,
            resume_snapshot=snap,
            question_kind="intro",
        )
    )
    s.commit()

    return jsonify(
        {
            "question_id": str(sid),
            "interview_run_id": str(sid),
            "question_kind": "intro",
            "question_text": pack["question_text"],
            "resume_summary": pack["resume_summary"],
            "role": role,
            "source": "resume",
        }
    )


@bp.post("/resume-next-question")
@limiter.limit("30 per hour")
def resume_next_question():
    """Next technical question in a resume-driven run (after self-intro round)."""
    if not _llm_configured(current_app):
        return _need_llm_response(current_app)

    data = request.get_json(silent=True) or {}
    rid_raw = (data.get("interview_run_id") or "").strip()
    try:
        run_uuid = uuid.UUID(rid_raw)
    except ValueError:
        return jsonify({"error": "Invalid or missing interview_run_id"}), 400

    s = _session()
    anchor = s.get(InterviewSession, run_uuid)
    if not anchor or anchor.interview_run_id != run_uuid:
        return jsonify(
            {"error": "Interview run not found. Start again from the Resume tab."}
        ), 404
    if (anchor.source_url or "").strip():
        return jsonify(
            {
                "error": "This run is from the Web tab. Use the web flow for the next question."
            }
        ), 400
    if not (anchor.resume_snapshot or "").strip():
        return jsonify(
            {"error": "This session has no stored resume context. Upload again."}
        ), 400

    asked = list(
        s.execute(
            select(InterviewSession.question_text).where(
                InterviewSession.interview_run_id == run_uuid
            )
        ).scalars().all()
    )

    try:
        tech = generate_resume_technical_question(
            anchor.role_text,
            anchor.resume_summary,
            anchor.resume_snapshot or "",
            asked,
            google_api_key=current_app.config.get("GOOGLE_API_KEY"),
            gemini_model=current_app.config["GEMINI_MODEL"],
            groq_api_key=current_app.config.get("GROQ_API_KEY"),
            groq_model=current_app.config["GROQ_MODEL"],
            hf_api_key=current_app.config.get("HUGGINGFACE_API_KEY"),
            hf_model=current_app.config["HUGGINGFACE_MODEL"],
            hf_base_url=current_app.config["HUGGINGFACE_BASE_URL"],
        )
    except Exception as e:
        current_app.logger.exception("resume technical question failed")
        return jsonify(
            {"error": "AI could not generate the next question", "detail": str(e)}
        ), 503

    sid = uuid.uuid4()
    s.add(
        InterviewSession(
            session_id=sid,
            role_text=anchor.role_text[:512],
            resume_summary=anchor.resume_summary,
            question_text=tech["question_text"],
            ideal_answer=tech["ideal_answer"],
            source_url=None,
            interview_run_id=run_uuid,
            resume_snapshot=anchor.resume_snapshot,
            question_kind="technical",
        )
    )
    s.commit()

    return jsonify(
        {
            "question_id": str(sid),
            "interview_run_id": str(run_uuid),
            "question_kind": "technical",
            "question_text": tech["question_text"],
            "resume_summary": anchor.resume_summary,
            "role": anchor.role_text,
            "source": "resume",
        }
    )


@bp.post("/prepare-from-web")
@limiter.limit("15 per hour")
def prepare_from_web():
    if not _llm_configured(current_app):
        return _need_llm_response(current_app)

    data = request.get_json(silent=True) or {}
    role = (data.get("role") or request.form.get("role") or "").strip()
    source_url = (data.get("source_url") or request.form.get("source_url") or "").strip()

    if not role:
        return jsonify({"error": "Missing role"}), 400
    if len(role) > 500:
        return jsonify({"error": "Role is too long"}), 400
    if not source_url:
        return jsonify({"error": "Missing source_url"}), 400

    try:
        final_url, page_text = fetch_page_text(source_url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception("web fetch failed")
        return jsonify({"error": "Could not fetch URL", "detail": str(e)}), 502

    try:
        pack = generate_question_from_web_text(
            role,
            page_text,
            final_url,
            google_api_key=current_app.config.get("GOOGLE_API_KEY"),
            gemini_model=current_app.config["GEMINI_MODEL"],
            groq_api_key=current_app.config.get("GROQ_API_KEY"),
            groq_model=current_app.config["GROQ_MODEL"],
            hf_api_key=current_app.config.get("HUGGINGFACE_API_KEY"),
            hf_model=current_app.config["HUGGINGFACE_MODEL"],
            hf_base_url=current_app.config["HUGGINGFACE_BASE_URL"],
        )
    except Exception as e:
        current_app.logger.exception("web question gen failed")
        return jsonify(
            {"error": "AI could not build a question from this page", "detail": str(e)}
        ), 503

    snap = page_text.strip()
    if len(snap) > 12000:
        snap = snap[:11997] + "..."

    sid = uuid.uuid4()
    s = _session()
    s.add(
        InterviewSession(
            session_id=sid,
            role_text=role[:512],
            resume_summary=pack["page_summary"],
            question_text=pack["question_text"],
            ideal_answer=pack["ideal_answer"],
            source_url=final_url[:2048],
            interview_run_id=sid,
            resume_snapshot=snap,
            question_kind="web",
        )
    )
    s.commit()

    return jsonify(
        {
            "question_id": str(sid),
            "interview_run_id": str(sid),
            "question_kind": "web",
            "question_text": pack["question_text"],
            "resume_summary": pack["page_summary"],
            "source_url": final_url,
            "role": role,
            "source": "web",
        }
    )


@bp.post("/web-next-question")
@limiter.limit("30 per hour")
def web_next_question():
    """Next question from the same scraped page (non-repeating within the run)."""
    if not _llm_configured(current_app):
        return _need_llm_response(current_app)

    data = request.get_json(silent=True) or {}
    rid_raw = (data.get("interview_run_id") or "").strip()
    try:
        run_uuid = uuid.UUID(rid_raw)
    except ValueError:
        return jsonify({"error": "Invalid or missing interview_run_id"}), 400

    s = _session()
    anchor = s.get(InterviewSession, run_uuid)
    if not anchor or anchor.interview_run_id != run_uuid:
        return jsonify(
            {"error": "Web session not found. Start again from the Web page tab."}
        ), 404
    if not (anchor.source_url or "").strip():
        return jsonify({"error": "Not a web-page interview session."}), 400
    if not (anchor.resume_snapshot or "").strip():
        return jsonify(
            {"error": "Session has no stored page text. Scrape the URL again."}
        ), 400

    asked = list(
        s.execute(
            select(InterviewSession.question_text).where(
                InterviewSession.interview_run_id == run_uuid
            )
        ).scalars().all()
    )

    try:
        nxt = generate_followup_web_question(
            anchor.role_text,
            anchor.resume_snapshot or "",
            (anchor.source_url or "")[:2048],
            anchor.resume_summary,
            asked,
            google_api_key=current_app.config.get("GOOGLE_API_KEY"),
            gemini_model=current_app.config["GEMINI_MODEL"],
            groq_api_key=current_app.config.get("GROQ_API_KEY"),
            groq_model=current_app.config["GROQ_MODEL"],
            hf_api_key=current_app.config.get("HUGGINGFACE_API_KEY"),
            hf_model=current_app.config["HUGGINGFACE_MODEL"],
            hf_base_url=current_app.config["HUGGINGFACE_BASE_URL"],
        )
    except Exception as e:
        current_app.logger.exception("web follow-up question failed")
        return jsonify(
            {"error": "AI could not generate the next question", "detail": str(e)}
        ), 503

    sid = uuid.uuid4()
    s.add(
        InterviewSession(
            session_id=sid,
            role_text=anchor.role_text[:512],
            resume_summary=anchor.resume_summary,
            question_text=nxt["question_text"],
            ideal_answer=nxt["ideal_answer"],
            source_url=(anchor.source_url or "")[:2048],
            interview_run_id=run_uuid,
            resume_snapshot=anchor.resume_snapshot,
            question_kind="web_followup",
        )
    )
    s.commit()

    return jsonify(
        {
            "question_id": str(sid),
            "interview_run_id": str(run_uuid),
            "question_kind": "web_followup",
            "question_text": nxt["question_text"],
            "resume_summary": anchor.resume_summary,
            "source_url": anchor.source_url,
            "role": anchor.role_text,
            "source": "web",
        }
    )


@bp.route("/get-question", methods=["GET"])
def get_question():
    role = (request.args.get("role") or "").strip()
    if not role:
        return jsonify({"error": "Missing role parameter"}), 400
    exclude_raw = (request.args.get("exclude") or "").strip()
    exclude_ids: list[uuid.UUID] = []
    for part in exclude_raw.split(",")[:80]:
        part = part.strip()
        if not part:
            continue
        try:
            exclude_ids.append(uuid.UUID(part))
        except ValueError:
            continue

    s = _session()
    qry = select(Question).where(Question.role_category == role)
    if exclude_ids:
        qry = qry.where(~Question.question_id.in_(exclude_ids))
    q = s.execute(qry.order_by(func.random()).limit(1)).scalar_one_or_none()
    if not q and exclude_ids:
        q = (
            s.execute(
                select(Question)
                .where(Question.role_category == role)
                .order_by(func.random())
                .limit(1)
            ).scalar_one_or_none()
        )
    if not q:
        return jsonify({"error": f"No questions found for role: {role}"}), 404
    return jsonify(
        {
            "question_id": str(q.question_id),
            "question_text": q.question_text,
            "role_category": q.role_category,
            "source": "bank",
        }
    )


@bp.post("/analyze-answer")
@limiter.limit("30 per hour")
def analyze_answer_route():
    is_video_field = bool(
        request.files.get("video") and request.files["video"].filename
    )
    media = None
    if is_video_field:
        media = request.files["video"]
    elif request.files.get("audio") and request.files["audio"].filename:
        media = request.files["audio"]
    if media is None:
        return jsonify(
            {"error": "Missing recording: send multipart field audio or video (WebM)"}
        ), 400
    qid_raw = request.form.get("question_id") or ""
    try:
        qid = uuid.UUID(qid_raw.strip())
    except ValueError:
        return jsonify({"error": "Invalid question_id"}), 400

    local_stt = bool(current_app.config.get("LOCAL_WHISPER"))
    if not local_stt and not _cfg_strip(current_app, "OPENAI_API_KEY") and not _cfg_strip(
        current_app, "GROQ_API_KEY"
    ):
        return jsonify(
            {
                "error": "Speech-to-text: set LOCAL_WHISPER=1 for open-source Whisper on the server, or add OPENAI_API_KEY and/or GROQ_API_KEY",
                "fix": "For fully local STT: pip install deps, set LOCAL_WHISPER=1, optional LOCAL_WHISPER_MODEL=base|small|…",
            }
        ), 503
    if not _llm_configured(current_app):
        return _need_llm_response(current_app)

    s = _session()
    q_text, ideal, _src = _resolve_question(s, qid)
    if not q_text or not ideal:
        return jsonify({"error": "Question not found"}), 404

    try:
        media.stream.seek(0)
        raw_bytes = media.read()
    except Exception:
        current_app.logger.exception("read upload failed")
        return jsonify({"error": "Could not read upload"}), 400

    if len(raw_bytes) < 256:
        return jsonify({"error": "Recording too short"}), 400

    fname = media.filename or "answer.webm"
    buf = BytesIO(raw_bytes)
    buf.name = fname
    fs = FileStorage(
        stream=buf,
        filename=fname,
        content_type=media.content_type or "application/octet-stream",
    )

    try:
        transcript = transcribe_audio(
            fs,
            openai_api_key=current_app.config.get("OPENAI_API_KEY"),
            groq_api_key=current_app.config.get("GROQ_API_KEY"),
            groq_whisper_model=current_app.config["GROQ_WHISPER_MODEL"],
            local_whisper=local_stt,
            local_whisper_model=current_app.config["LOCAL_WHISPER_MODEL"],
            local_whisper_device=current_app.config["LOCAL_WHISPER_DEVICE"],
            local_whisper_compute_type=current_app.config["LOCAL_WHISPER_COMPUTE_TYPE"],
        )
    except Exception as e:
        current_app.logger.exception("speech-to-text failed")
        return jsonify({"error": "Transcription failed", "detail": str(e)}), 503

    try:
        feedback = analyze_answer(
            q_text,
            transcript,
            ideal,
            google_api_key=current_app.config.get("GOOGLE_API_KEY"),
            gemini_model=current_app.config["GEMINI_MODEL"],
            groq_api_key=current_app.config.get("GROQ_API_KEY"),
            groq_model=current_app.config["GROQ_MODEL"],
            hf_api_key=current_app.config.get("HUGGINGFACE_API_KEY"),
            hf_model=current_app.config["HUGGINGFACE_MODEL"],
            hf_base_url=current_app.config["HUGGINGFACE_BASE_URL"],
        )
    except Exception as e:
        current_app.logger.exception("judge llm failed")
        return jsonify({"error": "Analysis failed", "detail": str(e)}), 503

    rid = uuid.uuid4()
    media_kind = "video" if is_video_field else "audio"
    raw_mime = (media.content_type or "").split(";")[0].strip()[:128]
    mime = raw_mime or ("video/webm" if is_video_field else "audio/webm")
    rel = f"recordings/{rid}.webm"
    rec_dir = os.path.join(current_app.instance_path, "recordings")
    cfg = current_app.config
    storage_backend = "local"
    abs_path = None
    if recording_storage_supabase_ready(cfg):
        try:
            upload_recording(cfg, rel, raw_bytes, mime)
            storage_backend = "supabase"
        except Exception:
            current_app.logger.exception(
                "supabase recording upload failed; using local file"
            )
            os.makedirs(rec_dir, exist_ok=True)
            abs_path = os.path.join(rec_dir, f"{rid}.webm")
            try:
                with open(abs_path, "wb") as out:
                    out.write(raw_bytes)
            except OSError as e:
                current_app.logger.exception("recording file write failed")
                return jsonify(
                    {"error": "Could not store recording", "detail": str(e)}
                ), 500
    else:
        os.makedirs(rec_dir, exist_ok=True)
        abs_path = os.path.join(rec_dir, f"{rid}.webm")
        try:
            with open(abs_path, "wb") as out:
                out.write(raw_bytes)
        except OSError as e:
            current_app.logger.exception("recording file write failed")
            return jsonify({"error": "Could not store recording", "detail": str(e)}), 500

    token = secrets.token_hex(32)
    row = InterviewRecording(
        recording_id=rid,
        question_id=qid,
        file_path=rel,
        media_kind=media_kind,
        mime_type=mime[:128],
        byte_size=len(raw_bytes),
        transcript=transcript,
        access_token=token,
        storage_backend=storage_backend,
    )
    s.add(row)
    try:
        s.commit()
    except Exception:
        current_app.logger.exception("recording metadata commit failed")
        s.rollback()
        if storage_backend == "supabase":
            try:
                remove_recording_object(cfg, rel)
            except Exception:
                current_app.logger.exception("supabase rollback remove failed")
        elif abs_path:
            try:
                os.remove(abs_path)
            except OSError:
                pass
        return jsonify({"error": "Could not save recording metadata"}), 500

    return jsonify(
        {
            **feedback,
            "transcript": transcript,
            "recording_id": str(rid),
            "recording_token": token,
            "recording_media_kind": media_kind,
        }
    )


@bp.get("/recording/<uuid:recording_id>/media")
def get_recording_media(recording_id: uuid.UUID):
    token = (request.args.get("token") or "").strip()
    s = _session()
    row = s.get(InterviewRecording, recording_id)
    if not row or not _recording_token_ok(token, row.access_token):
        return jsonify({"error": "Not found"}), 404
    backend = (getattr(row, "storage_backend", None) or "local").strip() or "local"
    if backend == "supabase":
        if not recording_storage_supabase_ready(current_app.config):
            return jsonify({"error": "Storage not configured"}), 503
        url = signed_recording_url(current_app.config, row.file_path, 3600)
        if not url:
            return jsonify({"error": "Could not create download URL"}), 502
        return redirect(url, code=302)
    abs_path = os.path.normpath(
        os.path.join(current_app.instance_path, row.file_path.replace("/", os.sep))
    )
    rec_root = os.path.normpath(os.path.join(current_app.instance_path, "recordings"))
    if not abs_path.startswith(rec_root + os.sep) and abs_path != rec_root:
        return jsonify({"error": "Not found"}), 404
    if not os.path.isfile(abs_path):
        return jsonify({"error": "File missing"}), 404
    return send_file(
        abs_path,
        mimetype=row.mime_type or "application/octet-stream",
        as_attachment=False,
        max_age=3600,
    )


@bp.get("/admin/recordings")
@limiter.limit("60 per minute")
def admin_list_recordings():
    if not _cfg_strip(current_app, "ADMIN_API_KEY"):
        return jsonify({"error": "Not found"}), 404
    if not _admin_key_ok():
        return jsonify({"error": "Forbidden"}), 403
    s = _session()
    rows = s.execute(
        select(InterviewRecording).order_by(InterviewRecording.created_at.desc()).limit(200)
    ).scalars().all()
    return jsonify(
        {
            "recordings": [
                {
                    "recording_id": str(r.recording_id),
                    "question_id": str(r.question_id),
                    "media_kind": r.media_kind,
                    "mime_type": r.mime_type,
                    "byte_size": r.byte_size,
                    "storage_backend": getattr(r, "storage_backend", None) or "local",
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "transcript_preview": (r.transcript or "")[:240],
                }
                for r in rows
            ]
        }
    )


@bp.get("/admin/recording/<uuid:recording_id>/media")
@limiter.limit("120 per minute")
def admin_get_recording_media(recording_id: uuid.UUID):
    if not _cfg_strip(current_app, "ADMIN_API_KEY"):
        return jsonify({"error": "Not found"}), 404
    if not _admin_key_ok():
        return jsonify({"error": "Forbidden"}), 403
    s = _session()
    row = s.get(InterviewRecording, recording_id)
    if not row:
        return jsonify({"error": "Not found"}), 404
    backend = (getattr(row, "storage_backend", None) or "local").strip() or "local"
    if backend == "supabase":
        if not recording_storage_supabase_ready(current_app.config):
            return jsonify({"error": "Storage not configured"}), 503
        url = signed_recording_url(current_app.config, row.file_path, 3600)
        if not url:
            return jsonify({"error": "Could not create download URL"}), 502
        return redirect(url, code=302)
    abs_path = os.path.normpath(
        os.path.join(current_app.instance_path, row.file_path.replace("/", os.sep))
    )
    rec_root = os.path.normpath(os.path.join(current_app.instance_path, "recordings"))
    if not abs_path.startswith(rec_root + os.sep):
        return jsonify({"error": "Not found"}), 404
    if not os.path.isfile(abs_path):
        return jsonify({"error": "File missing"}), 404
    return send_file(
        abs_path,
        mimetype=row.mime_type or "application/octet-stream",
        as_attachment=False,
        max_age=0,
    )
