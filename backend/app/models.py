import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Uuid, func
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
