import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Enum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from inti.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), default="local")
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    repo_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="planned",
    )
    profile: Mapped[str] = mapped_column(
        String(32),
        default="pro_mix",
    )
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    autonomy_level: Mapped[str] = mapped_column(
        String(32),
        default="human_gatekeeper",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    steps: Mapped[list["JobStep"]] = relationship(
        "JobStep", back_populates="job", order_by="JobStep.order", cascade="all, delete-orphan"
    )
    diffs: Mapped[list["Diff"]] = relationship("Diff", back_populates="job", cascade="all, delete-orphan")
    approvals: Mapped[list["Approval"]] = relationship("Approval", back_populates="job", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship("Event", back_populates="job", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="job", cascade="all, delete-orphan")
    ci_runs: Mapped[list["CiRun"]] = relationship("CiRun", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Job {self.id} [{self.status}] {self.title}>"
