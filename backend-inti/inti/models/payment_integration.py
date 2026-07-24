import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from inti.database import Base


class PaymentIntegration(Base):
    __tablename__ = "payment_integrations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    psp_name: Mapped[str] = mapped_column(String(64))
    psp_display_name: Mapped[str] = mapped_column(String(128), default="")
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="planned"
    )
    test_mode: Mapped[bool] = mapped_column(default=True)
    environment: Mapped[str] = mapped_column(String(16), default="sandbox")
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PaymentIntegration {self.id} [{self.psp_name}] {self.status}>"
