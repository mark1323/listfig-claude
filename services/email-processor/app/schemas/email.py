"""Email schemas for API validation"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


class EmailWebhook(BaseModel):
    """Schema for incoming email webhook from Haraka"""

    message_id: str = Field(..., description="Unique message ID")
    from_address: str = Field(..., alias="from", description="Sender email address")
    to_addresses: List[str] = Field(..., alias="to", description="Recipient email addresses")
    subject: str = Field(default="", description="Email subject")
    headers: dict = Field(default_factory=dict, description="Email headers")
    text: str = Field(default="", description="Plain text body")
    html: str = Field(default="", description="HTML body")
    received_at: str = Field(..., description="Timestamp when email was received")

    class Config:
        populate_by_name = True


class EmailResponse(BaseModel):
    """Schema for email response"""

    id: UUID
    message_id: str
    from_address: str
    to_address: str
    subject: Optional[str]
    received_at: datetime
    status: str

    # AI-generated content
    ai_summary: Optional[str]
    ai_category: Optional[str]
    ai_metadata: Optional[dict]

    # Processing metadata
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    error_message: Optional[str]

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    """Schema for paginated email list"""

    emails: List[EmailResponse]
    total: int
    limit: int
    offset: int
