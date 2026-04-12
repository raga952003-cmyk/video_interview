import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Question(Base):
    __tablename__ = "questions"

    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    role_category: Mapped[str] = mapped_column(String(255), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    scraped_ideal_answer: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class InterviewSession(Base):
    """Resume-driven question; ideal_answer stays server-side until grading."""

    __tablename__ = "interview_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    role_text: Mapped[str] = mapped_column(String(512))
    resume_summary: Mapped[str] = mapped_column(Text)
    question_text: Mapped[str] = mapped_column(Text)
    ideal_answer: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Resume multi-round: all rows in a run share interview_run_id (= first session_id).
    interview_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True, index=True
    )
    resume_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class InterviewRecording(Base):
    """
    Metadata for a saved answer clip. File bytes are stored under instance_path;
    use PostgreSQL or SQLite for this table — not BLOBs inside the DB for large videos.
    """

    __tablename__ = "interview_recordings"

    recording_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    file_path: Mapped[str] = mapped_column(String(512))
    media_kind: Mapped[str] = mapped_column(String(16))
    mime_type: Mapped[str] = mapped_column(String(128))
    byte_size: Mapped[int] = mapped_column(Integer, default=0)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token: Mapped[str] = mapped_column(String(64), index=True)
    # "local" = file under Flask instance_path; "supabase" = object at file_path in bucket
    storage_backend: Mapped[str] = mapped_column(String(32), default="local")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
