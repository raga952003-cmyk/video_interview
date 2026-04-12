import os

from flask import Flask, Response, abort, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from app.config import Config, sync_env_into_app
from app.limiter_ext import limiter
from app.models import Base


def _spa_dist_dir(cfg: dict) -> str | None:
    raw = (cfg.get("FRONTEND_DIST") or "").strip()
    if not raw:
        return None
    absd = os.path.abspath(raw)
    return absd if os.path.isdir(absd) else None


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    sync_env_into_app(app)

    os.makedirs(app.instance_path, exist_ok=True)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    engine_kw: dict = {"pool_pre_ping": True}
    # Flask dev server handles requests on different threads; SQLite defaults
    # forbid using one connection across threads → 500 on /api/* without this.
    if db_uri.startswith("sqlite:"):
        engine_kw["connect_args"] = {"check_same_thread": False}

    engine = create_engine(db_uri, **engine_kw)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)

    app.extensions["engine"] = engine
    app.extensions["Session"] = Session

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [o.strip() for o in app.config["CORS_ORIGINS"] if o.strip()],
            }
        },
        supports_credentials=True,
    )

    limiter.init_app(app)

    from app.routes import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/")
    def root():
        """Serve built SPA when FRONTEND_DIST is set; otherwise JSON for API discovery."""
        dist = _spa_dist_dir(app.config)
        if dist and os.path.isfile(os.path.join(dist, "index.html")):
            return send_from_directory(dist, "index.html")
        return jsonify(
            service="ai-interview-coach-api",
            health="/api/health",
            roles="/api/roles",
        )

    @app.get("/favicon.ico")
    def favicon():
        """Browsers request this automatically; Flask has no static favicon by default."""
        return Response(status=204)

    dist = _spa_dist_dir(app.config)
    if dist:

        @app.get("/<path:path>")
        def spa_static(path: str):
            from werkzeug.utils import safe_join

            if path.startswith("api/"):
                abort(404)
            candidate = safe_join(dist, path)
            if candidate is not None and os.path.isfile(candidate):
                return send_from_directory(dist, path)
            index = os.path.join(dist, "index.html")
            if os.path.isfile(index):
                return send_from_directory(dist, "index.html")
            abort(404)

    @app.teardown_appcontext
    def remove_session(_exc=None):
        Session.remove()

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_e):
        from flask import jsonify

        return jsonify({"error": "File too large"}), 413

    with app.app_context():
        Base.metadata.create_all(bind=engine)
        _ensure_sqlite_interview_sessions_source_url(engine)
        _ensure_sqlite_interview_sessions_resume_round_cols(engine)

    return app


def _ensure_sqlite_interview_sessions_source_url(engine) -> None:
    """Add source_url to interview_sessions on existing SQLite DBs."""
    if engine.dialect.name != "sqlite":
        return
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("interview_sessions"):
        return
    cols = {c["name"] for c in insp.get_columns("interview_sessions")}
    if "source_url" in cols:
        return
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE interview_sessions ADD COLUMN source_url VARCHAR(2048)")
        )


def _ensure_sqlite_interview_sessions_resume_round_cols(engine) -> None:
    """Add resume multi-round columns on existing SQLite DBs."""
    if engine.dialect.name != "sqlite":
        return
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("interview_sessions"):
        return
    cols = {c["name"] for c in insp.get_columns("interview_sessions")}
    alters = []
    if "interview_run_id" not in cols:
        alters.append("ALTER TABLE interview_sessions ADD COLUMN interview_run_id VARCHAR(36)")
    if "resume_snapshot" not in cols:
        alters.append("ALTER TABLE interview_sessions ADD COLUMN resume_snapshot TEXT")
    if "question_kind" not in cols:
        alters.append(
            "ALTER TABLE interview_sessions ADD COLUMN question_kind VARCHAR(32)"
        )
    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))
