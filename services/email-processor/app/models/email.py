"""Email database model"""
import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID


class EmailStatus(str, enum.Enum):
    """Email processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Email(Base):
    """Email model for storing received and processed emails"""

    __tablename__ = "emails"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Email identifiers
    message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Email addresses
    from_address: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    to_address: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    # Email content
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    html_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    # Processing status
    status: Mapped[EmailStatus] = mapped_column(
        SQLEnum(EmailStatus, name="email_status"),
        default=EmailStatus.PENDING,
        index=True,
        nullable=False,
    )

    # AI-generated content
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Processing metadata
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Email(id={self.id}, message_id={self.message_id}, from={self.from_address})>"
