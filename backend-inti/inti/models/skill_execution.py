import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from inti.database import Base


class SkillExecution(Base):
    __tablename__ = "skill_executions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    skill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("skill_definitions.id"), index=True
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=True
    )
    result: Mapped[str] = mapped_column(String(16), default="success")
    ci_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<SkillExecution {self.skill_id} [{self.result}]>"
