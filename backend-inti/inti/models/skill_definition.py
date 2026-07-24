import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from inti.database import Base


class SkillDefinition(Base):
    __tablename__ = "skill_definitions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    best_practices_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<SkillDefinition {self.name} [{self.success_rate:.0%}]>"
