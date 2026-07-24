import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from inti.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255))
    project_type: Mapped[str] = mapped_column(
        String(32), default="dopaweb_theme"
    )
    repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dopaweb_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    erp_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    erp_auth_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    deploy_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.id} [{self.project_type}] {self.name}>"
