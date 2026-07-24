import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from inti.database import Base


class ExperienceLesson(Base):
    __tablename__ = "experience_lessons"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    lesson_positive: Mapped[str | None] = mapped_column(Text, nullable=True)
    lesson_negative: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    job: Mapped["Job"] = relationship("Job")

    def __repr__(self) -> str:
        return f"<ExperienceLesson {self.id} job={self.job_id}>"
