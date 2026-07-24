import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from inti.database import Base


class Diff(Base):
    __tablename__ = "diffs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True)
    step_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("job_steps.id"), nullable=True
    )
    summary: Mapped[str] = mapped_column(String(500), default="")
    diff_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    files_changed: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="generated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    job: Mapped["Job"] = relationship("Job", back_populates="diffs")
    approvals: Mapped[list["Approval"]] = relationship("Approval", back_populates="diff")

    def __repr__(self) -> str:
        return f"<Diff {self.id} [{self.status}]>"
