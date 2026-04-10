import os

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_default_sqlite_path = os.path.join(_backend_dir, "instance", "interview_coach.db")
_default_sqlite_uri = "sqlite:///" + _default_sqlite_path.replace("\\", "/")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", _default_sqlite_uri)
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "25")) * 1024 * 1024
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    QDRANT_URL = (os.environ.get("QDRANT_URL") or "").strip().rstrip("/")
    QDRANT_API_KEY = (os.environ.get("QDRANT_API_KEY") or "").strip()
    GROQ_API_KEY = (os.environ.get("GROQ_API_KEY") or "").strip()
    GROQ_MODEL = (os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile").strip()
    GROQ_WHISPER_MODEL = (
        os.environ.get("GROQ_WHISPER_MODEL") or "whisper-large-v3"
    ).strip()
    HUGGINGFACE_API_KEY = (os.environ.get("HUGGINGFACE_API_KEY") or "").strip()
    HUGGINGFACE_MODEL = (
        os.environ.get("HUGGINGFACE_MODEL") or "meta-llama/Meta-Llama-3.1-8B-Instruct"
    ).strip()
    HUGGINGFACE_BASE_URL = (
        os.environ.get("HUGGINGFACE_BASE_URL") or "https://router.huggingface.co/v1"
    ).strip().rstrip("/")
    MISTRAL_API_KEY = (os.environ.get("MISTRAL_API_KEY") or "").strip()


def sync_env_into_app(app) -> None:
    """
    Re-apply environment variables to Flask app.config after from_object(Config).

    Needed because the Config class body runs at import time; Flask's debug reloader
    can import the app package before run.py's load_dotenv() has run in that process.
    """
    uri = os.environ.get("DATABASE_URL", _default_sqlite_uri)
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me")
    app.config["MAX_CONTENT_LENGTH"] = (
        int(os.environ.get("MAX_UPLOAD_MB", "25")) * 1024 * 1024
    )
    app.config["OPENAI_API_KEY"] = (os.environ.get("OPENAI_API_KEY") or "").strip()
    app.config["GOOGLE_API_KEY"] = (os.environ.get("GOOGLE_API_KEY") or "").strip()
    app.config["GEMINI_MODEL"] = (
        os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash"
    ).strip()
    cors = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    app.config["CORS_ORIGINS"] = [x.strip() for x in cors.split(",") if x.strip()]
    app.config["QDRANT_URL"] = (os.environ.get("QDRANT_URL") or "").strip().rstrip("/")
    app.config["QDRANT_API_KEY"] = (os.environ.get("QDRANT_API_KEY") or "").strip()
    app.config["GROQ_API_KEY"] = (os.environ.get("GROQ_API_KEY") or "").strip()
    app.config["GROQ_MODEL"] = (
        os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile"
    ).strip()
    app.config["GROQ_WHISPER_MODEL"] = (
        os.environ.get("GROQ_WHISPER_MODEL") or "whisper-large-v3"
    ).strip()
    app.config["HUGGINGFACE_API_KEY"] = (
        os.environ.get("HUGGINGFACE_API_KEY") or ""
    ).strip()
    app.config["HUGGINGFACE_MODEL"] = (
        os.environ.get("HUGGINGFACE_MODEL") or "meta-llama/Meta-Llama-3.1-8B-Instruct"
    ).strip()
    app.config["HUGGINGFACE_BASE_URL"] = (
        os.environ.get("HUGGINGFACE_BASE_URL") or "https://router.huggingface.co/v1"
    ).strip().rstrip("/")
    app.config["MISTRAL_API_KEY"] = (os.environ.get("MISTRAL_API_KEY") or "").strip()
