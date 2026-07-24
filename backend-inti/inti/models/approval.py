import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from inti.database import Base


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True)
    diff_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("diffs.id"), nullable=True
    )
    approved_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_by_device_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approval_type: Mapped[str] = mapped_column(String(32), default="human_mobile")
    decision: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    signature: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    job: Mapped["Job"] = relationship("Job", back_populates="approvals")
    diff: Mapped["Diff"] = relationship("Diff", back_populates="approvals")

    def __repr__(self) -> str:
        return f"<Approval {self.id} [{self.decision}]>"
